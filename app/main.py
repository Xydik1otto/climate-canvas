"""FastAPI application and JSON API for the dashboard."""
from __future__ import annotations

import csv
import io
import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import cache as cache_mod
from . import climate, config, demo_data, discover, floors, ha_client, mqtt_ingest, openmeteo, report_html, report_pdf, sync

_cache: cache_mod.Cache | None = None
_pull_thread: threading.Thread | None = None


def get_cache() -> cache_mod.Cache:
    global _cache
    if _cache is None:
        _cache = cache_mod.Cache(config.DB_PATH)
        if not config.DEMO:
            sync.pull_once(_cache, config.load_rooms())
    return _cache


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup/shutdown via lifespan (replaces deprecated on_event)."""
    global _pull_thread
    get_cache()
    _pull_thread = sync.start_hourly_pull(_cache, config.load_rooms)
    yield


app = FastAPI(title="climate-canvas", version="1.0.0", lifespan=lifespan)


def cli() -> None:
    """Console entry point: `climate-canvas [--host H] [--port P] [--demo]`."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(prog="climate-canvas", description="Home Climate & Energy Canvas")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8321, help="port (default: 8321)")
    parser.add_argument("--demo", action="store_true", help="force demo mode (synthetic data)")
    args = parser.parse_args()
    if args.demo:
        import os

        os.environ["DEMO"] = "1"
        config._ENV_DEMO = True
        config.DEMO = True
    uvicorn.run("app.main:app", host=args.host, port=args.port)


@app.get("/api/health")
def health() -> dict:
    cache = get_cache()
    return {"status": "ok", "demo": config.DEMO, "has_data": cache.count() > 0}


@app.post("/api/demo/seed")
def demo_seed() -> dict:
    """First-run opt-in: fill the cache with deterministic demo history."""
    if not config.DEMO:
        raise HTTPException(409, "Home Assistant is configured — demo data would mix with real readings")
    cache = get_cache()
    before = cache.count()
    demo_data.seed_cache(cache, config.load_rooms())
    return {"status": "ok", "points": cache.count() - before}


# ---------- Setup wizard (Home Assistant URL + token, saved in settings.json) ----------

def _token_hint(token: str) -> str:
    """Masked hint for the UI — never return the real token."""
    return f"••••{token[-4:]}" if token else ""


@app.get("/api/setup")
def get_setup() -> dict:
    """Current HA connection config for the wizard (token is never returned)."""
    token = config.hass_token()
    return {
        "url": config.hass_url(),
        "token_set": bool(token),
        "token_hint": _token_hint(token),
        "from_env": bool(config._ENV_HASS_TOKEN or config._ENV_HASS_URL != "http://supervisor/core/api"),
        "demo": config.DEMO,
        "restart_required": False,
    }


@app.post("/api/setup")
def save_setup(payload: dict) -> dict:
    """Persist HA URL + long-lived access token to data/settings.json.

    Body: {"url": str, "token": str}. The demo<->HA switch itself takes effect
    after a restart; `restart_required` tells the UI when that is the case.
    """
    data = payload or {}
    url, token = data.get("url"), data.get("token")
    if not isinstance(url, str) or not url.strip().startswith(("http://", "https://")):
        raise HTTPException(422, 'body must be {"url": "http://…", "token": str}')
    if not isinstance(token, str) or not token.strip():
        raise HTTPException(422, "token must be a non-empty string")
    was_demo = config.DEMO
    config.save_settings({"hass_url": config.normalize_hass_url(url), "hass_token": token.strip()})
    config.reload()
    return {
        "status": "ok",
        "url": config.hass_url(),
        "token_hint": _token_hint(config.hass_token()),
        "restart_required": was_demo != config.demo_mode(),
    }


@app.post("/api/setup/test")
def test_setup(payload: dict) -> dict:
    """Test a HA connection (uses posted url/token or the saved ones)."""
    data = payload or {}
    url = data.get("url") or config.hass_url()
    token = data.get("token") or config.hass_token()
    if not isinstance(url, str) or not isinstance(token, str) or not url.strip():
        raise HTTPException(422, 'body must be {"url": str, "token": str} (or empty to test the saved config)')
    result = ha_client.test_connection(url.strip(), token)
    return result


METRIC_KEYS = {
    "temperature": "temp_entity",
    "humidity": "humidity_entity",
    "energy": "energy_entity",
    "co2": "co2_entity",
    "voc": "voc_entity",
}


def _room_metric(room: str, metric: str) -> str:
    rooms = config.load_rooms()
    cfg = rooms.get(room)
    if cfg is None:
        raise HTTPException(404, f"unknown room: {room}")
    entity = cfg.get(METRIC_KEYS.get(metric, ""))
    if not entity:
        raise HTTPException(404, f"room {room!r} has no {metric} sensor configured")
    return entity


@app.get("/api/rooms")
def rooms() -> dict:
    """Current temperature/humidity per room with comfort zones."""
    rooms_cfg = config.load_rooms()
    out = {}
    def enrich(room: str, t, h, extra: dict) -> dict:
        cfg = rooms_cfg.get(room, {})
        out = {
            **extra,
            "comfort": [config.COMFORT_MIN, config.COMFORT_MAX],
            "humidity_comfort": [
                float(cfg.get("humidity_min", config.HUMIDITY_MIN)),
                float(cfg.get("humidity_max", config.HUMIDITY_MAX)),
            ],
        }
        if t is not None and h is not None:
            out["dew_point"] = climate.dew_point(t, h)
            out["mold_risk"] = climate.mold_risk(t, h)
        else:
            out["dew_point"] = None
            out["mold_risk"] = None
        out["floor"] = cfg.get("floor") if isinstance(cfg, dict) else None
        return out

    if config.DEMO:
        now = datetime.now(timezone.utc)
        for room in rooms_cfg:
            st = demo_data.current_state(room, now)
            out[room] = enrich(room, st.get("temperature"), st.get("humidity"), st)
    else:
        try:
            states = ha_client.fetch_states()
        except Exception:
            states = {}
        for room, cfg in rooms_cfg.items():
            t = (states.get(cfg["temp_entity"]) or {}).get("temperature")
            h = (states.get(cfg["humidity_entity"]) or {}).get("humidity")
            c = (states.get(cfg.get("co2_entity") or "") or {}).get("co2")
            v = (states.get(cfg.get("voc_entity") or "") or {}).get("voc")
            out[room] = enrich(room, t, h, {"temperature": t, "humidity": h, "co2": c, "voc": v})
    return {"rooms": out, "demo": config.DEMO}


@app.get("/api/floors")
def floors_view() -> dict:
    """Кімнати, згруповані за поверхами (+ середні поточні значення поверху)."""
    rooms_cfg = config.load_rooms()
    current = floors.current_room_values()
    return {"floors": floors.floor_summary(rooms_cfg, current), "demo": config.DEMO}


@app.get("/api/timeline")
def timeline(
    room: str = Query(...),
    metric: str = Query("temperature", pattern="^(temperature|humidity|co2|voc)$"),
    days: int = Query(7, ge=1, le=365),
) -> dict:
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    series = cache.hourly_since(room, metric, since)
    return {"room": room, "metric": metric, "days": days, "points": series}


HEAT_METRICS = r"^(temperature|humidity|co2|voc|dew_point|mold_risk)$"


def _dew_or_risk_points(cache: cache_mod.Cache, room: str, since: str, metric: str) -> list[tuple[str, float]]:
    """Join cached temperature+humidity hourly means and derive dew point / mold risk."""
    tpts = cache.hourly_since(room, "temperature", since)
    hpts = dict(cache.hourly_since(room, "humidity", since))
    out = []
    for ts, t in tpts:
        h = hpts.get(ts)
        if h is None:
            continue
        if metric == "dew_point":
            out.append((ts, climate.dew_point(t, h)))
        else:
            out.append((ts, float(climate.RISK_LEVEL[climate.mold_risk(t, h)])))
    return out


@app.get("/api/heatmap")
def heatmap(
    room: str = Query(...),
    metric: str = Query("temperature", pattern=HEAT_METRICS),
    days: int = Query(90, ge=1, le=365),
) -> dict:
    if metric in ("dew_point", "mold_risk"):
        _room_metric(room, "temperature")  # validates room name
        _room_metric(room, "humidity")
        cache = get_cache()
        since = cache_mod.hours_ago_iso(days * 24)
        return cache_mod.heatmap_matrix(_dew_or_risk_points(cache, room, since, metric), days)
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    return cache.heatmap_since(room, metric, since, days)


@app.get("/api/seasons")
def seasons(
    room: str = Query(...),
    metric: str = Query("temperature", pattern="^(temperature|humidity|co2|voc)$"),
    month: int = Query(1, ge=1, le=12),
) -> dict:
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = "1970-01-01T00:00:00+00:00"
    points = [(ts, v) for ts, v in cache.since(room, metric, since) if int(ts[5:7]) == month]
    return {"room": room, "metric": metric, "month": month, "by_year": cache_mod.seasonal_means(points)}


@app.get("/api/outdoor")
def outdoor(days: int = Query(7, ge=1, le=365)) -> dict:
    """Outdoor temperature series (Open-Meteo, free/no key) for timeline overlay."""
    if config.DEMO:
        end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(days=days)
        points, source = [], "demo"
        ts = start
        while ts <= end:
            points.append([ts.strftime("%Y-%m-%dT%H:00:00+00:00"), demo_data.outdoor_hour(ts)])
            ts += timedelta(hours=1)
    else:
        points, source = _outdoor_cached(days)
    return {
        "days": days,
        "points": points,
        "source": source,
        "location": [config.LATITUDE, config.LONGITUDE],
    }


_OUTDOOR_CACHE: dict = {"key": None, "ts": 0.0, "points": []}
_OUTDOOR_TTL = 3600.0  # seconds — Open-Meteo archive updates a few times a day


def _outdoor_cached(days: int) -> tuple[list, str]:
    """In-memory 1h cache around the Open-Meteo archive fetch (non-demo only)."""
    import time as _time

    key = (config.LATITUDE, config.LONGITUDE, days)
    now = _time.time()
    if _OUTDOOR_CACHE["key"] == key and now - _OUTDOOR_CACHE["ts"] < _OUTDOOR_TTL:
        return _OUTDOOR_CACHE["points"], "open-meteo"
    points = [[ts, v] for ts, v in openmeteo.fetch_archive(days)]
    _OUTDOOR_CACHE.update(key=key, ts=now, points=points)
    return points, "open-meteo"


@app.get("/api/forecast")
def forecast(hours: int = Query(48, ge=6, le=168)) -> dict:
    """Outdoor temperature forecast (Open-Meteo, free/no key) for the next `hours` hours."""
    if config.DEMO:
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        points = []
        ts = start
        for _ in range(hours):
            points.append([ts.strftime("%Y-%m-%dT%H:00:00+00:00"), demo_data.outdoor_hour(ts)])
            ts += timedelta(hours=1)
        source = "demo"
    else:
        points = [[ts, v] for ts, v in openmeteo.fetch_forecast(hours)]
        source = "open-meteo"
    return {
        "hours": hours,
        "points": points,
        "source": source,
        "location": [config.LATITUDE, config.LONGITUDE],
    }


@app.get("/api/report/weekly")
def weekly_report() -> dict:
    """Auto-generated weekly report: avg/min/max per room + daily series for the SVG chart."""
    return weekly_report_data()


def weekly_report_data() -> dict:
    """Aggregate the last 7 days per room (shared by /weekly and the PDF export)."""
    cache = get_cache()
    since = cache_mod.hours_ago_iso(7 * 24)
    out: dict[str, dict] = {}
    for room in config.load_rooms():
        tpts = cache.since(room, "temperature", since)
        if not tpts:
            continue
        vals = [v for _, v in tpts]
        daily: dict[str, list[float]] = {}
        for ts, v in tpts:
            daily.setdefault(ts[:10], []).append(v)
        entry = {
            "avg": round(sum(vals) / len(vals), 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "samples": len(vals),
            "daily": [[d, round(sum(v) / len(v), 2)] for d, v in sorted(daily.items())],
        }
        hpts = cache.since(room, "humidity", since)
        if hpts:
            hvals = [v for _, v in hpts]
            entry["humidity_avg"] = round(sum(hvals) / len(hvals), 2)
        out[room] = entry
    return {"days": 7, "rooms": out}


@app.get("/api/report/weekly.pdf")
def weekly_report_pdf() -> Response:
    """Download the weekly report as a PDF (reportlab, generated on the fly)."""
    pdf_bytes = report_pdf.build_pdf(weekly_report_data())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="climate-canvas-weekly-{stamp}.pdf"'},
    )


@app.get("/api/report/weekly.html")
def weekly_report_html() -> Response:
    """Download the weekly report as a self-contained HTML file (inline styles)."""
    html_text = report_html.build_html(weekly_report_data())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Response(
        html_text,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="climate-canvas-weekly-{stamp}.html"'},
    )


@app.get("/api/smtp")
def get_smtp() -> dict:
    """Saved SMTP settings for the optional report email (password masked)."""
    s = config.load_settings()
    password = s.get("smtp_password", "")
    return {
        "host": s.get("smtp_host", ""),
        "port": s.get("smtp_port", 587),
        "user": s.get("smtp_user", ""),
        "from": s.get("smtp_from", ""),
        "tls": s.get("smtp_tls", True),
        "password_set": bool(password),
        "password_hint": f"••••{password[-3:]}" if password else "",
    }


SMTP_KEYS = ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from", "smtp_tls")


@app.post("/api/smtp")
def save_smtp(payload: dict) -> dict:
    """Persist SMTP settings (optional email delivery of the weekly report)."""
    data = payload or {}
    update: dict = {}
    for key in SMTP_KEYS:
        if key in data:
            if key == "smtp_port":
                try:
                    update[key] = int(data[key])
                except (TypeError, ValueError):
                    raise HTTPException(422, "smtp_port must be an integer")
            elif key == "smtp_tls":
                update[key] = bool(data[key])
            else:
                if not isinstance(data[key], str):
                    raise HTTPException(422, f"{key} must be a string")
                update[key] = data[key]
    if not update:
        raise HTTPException(422, "nothing to save: body has none of " + ", ".join(SMTP_KEYS))
    config.save_settings(update)
    return {"status": "ok", "saved": [k for k in update if not k.endswith("password")]}


@app.post("/api/report/email")
def email_weekly_report(payload: dict) -> dict:
    """Email the weekly PDF report (SMTP required: posted or saved in settings).

    Body: {"to": str, "format": "pdf"|"html" (optional, default pdf), plus
    optional smtp_host/smtp_port/smtp_user/smtp_password/smtp_from/smtp_tls
    to override the saved settings}.
    """
    data = payload or {}
    to = data.get("to")
    if not isinstance(to, str) or "@" not in to:
        raise HTTPException(422, 'body must be {"to": "you@example.com", "smtp_*": optional overrides}')
    fmt = data.get("format", "pdf")
    if fmt not in ("pdf", "html"):
        raise HTTPException(422, 'format must be "pdf" or "html"')
    saved = config.load_settings()
    cfg = {
        "host": data.get("smtp_host") or saved.get("smtp_host"),
        "port": data.get("smtp_port") or saved.get("smtp_port", 587),
        "user": data.get("smtp_user", saved.get("smtp_user", "")),
        "password": data.get("smtp_password", saved.get("smtp_password", "")),
        "from": data.get("smtp_from") or saved.get("smtp_from") or "climate-canvas@localhost",
        "tls": data.get("smtp_tls", saved.get("smtp_tls", True)),
    }
    if not cfg["host"]:
        raise HTTPException(400, "SMTP is not configured: fill the SMTP settings or add smtp_host to the request")
    if fmt == "pdf":
        body = report_pdf.build_pdf(weekly_report_data())
        try:
            msg_id = report_pdf.send_email(cfg, to, body)
        except Exception as exc:  # noqa: BLE001 — surface SMTP errors to the UI
            raise HTTPException(502, f"SMTP error: {exc}")
    else:
        body = report_html.build_html(weekly_report_data())
        try:
            msg_id = report_pdf.send_html_email(cfg, to, body)
        except Exception as exc:  # noqa: BLE001 — surface SMTP errors to the UI
            raise HTTPException(502, f"SMTP error: {exc}")
    return {"status": "ok", "to": to, "format": fmt, "message_id": msg_id}


# ---------- MQTT ingestion (Zigbee2MQTT sensors → local cache) ----------

MQTT_KEYS = ("mqtt_enabled", "mqtt_host", "mqtt_port", "mqtt_topic_prefix", "mqtt_rooms")


@app.get("/api/mqtt")
def get_mqtt() -> dict:
    """Saved MQTT/Zigbee2MQTT ingestion settings (no broker connection here)."""
    s = config.load_settings()
    return {
        "enabled": bool(s.get("mqtt_enabled", False)),
        "host": s.get("mqtt_host", ""),
        "port": s.get("mqtt_port", 1883),
        "topic_prefix": s.get("mqtt_topic_prefix", mqtt_ingest.DEFAULT_PREFIX),
        "rooms": s.get("mqtt_rooms", {}),
        "paho_installed": _paho_available(),
    }


@app.post("/api/mqtt")
def save_mqtt(payload: dict) -> dict:
    """Persist MQTT settings. Body: {"mqtt_enabled": bool, "mqtt_host": str,
    "mqtt_port": int, "mqtt_topic_prefix": str, "mqtt_rooms": {friendly_name: room}}."""
    data = payload or {}
    update: dict = {}
    for key in MQTT_KEYS:
        if key not in data:
            continue
        value = data[key]
        if key == "mqtt_enabled":
            update[key] = bool(value)
        elif key == "mqtt_port":
            try:
                port = int(value)
            except (TypeError, ValueError):
                raise HTTPException(422, "mqtt_port must be an integer")
            if not 1 <= port <= 65535:
                raise HTTPException(422, "mqtt_port must be in 1..65535")
            update[key] = port
        elif key in ("mqtt_host", "mqtt_topic_prefix"):
            if not isinstance(value, str):
                raise HTTPException(422, f"{key} must be a string")
            update[key] = value.strip()
        elif key == "mqtt_rooms":
            if not isinstance(value, dict) or not all(
                isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in value.items()
            ):
                raise HTTPException(422, "mqtt_rooms must be {friendly_name: room_name} (non-empty strings)")
            update[key] = value
    if not update:
        raise HTTPException(422, "nothing to save: body has none of " + ", ".join(MQTT_KEYS))
    config.save_settings(update)
    return {"status": "ok", "saved": [k for k in update if k != "mqtt_rooms"] or ["mqtt_rooms"]}


@app.post("/api/mqtt/ingest")
def mqtt_ingest_manual(payload: dict) -> dict:
    """Inject one Zigbee2MQTT message through the real pipeline (no broker).

    Body: {"topic": "zigbee2mqtt/<Friendly Name>", "payload": "<json string or object>"}.
    Uses the saved mqtt_rooms mapping; returns how many readings were stored.
    """
    data = payload or {}
    topic, body = data.get("topic"), data.get("payload")
    if not isinstance(topic, str) or not topic.strip():
        raise HTTPException(422, 'body must be {"topic": str, "payload": json string or object}')
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False)
    if not isinstance(body, str):
        raise HTTPException(422, "payload must be a JSON string or a JSON object")
    saved = config.load_settings()
    ingestor = mqtt_ingest.MqttIngestor(
        get_cache(),
        saved.get("mqtt_rooms", {}),
        saved.get("mqtt_topic_prefix", mqtt_ingest.DEFAULT_PREFIX),
    )
    added = ingestor.handle(topic.strip(), body)
    if added == 0:
        raise HTTPException(422, "nothing ingested: check topic prefix and mqtt_rooms mapping")
    return {"status": "ok", "added": added}


def _paho_available() -> bool:
    try:
        import paho.mqtt.client  # noqa: F401
        return True
    except ImportError:
        return False


@app.get("/api/compare")
def compare_rooms(
    metric: str = Query("temperature", pattern="^(temperature|humidity)$"),
    days: int = Query(7, ge=1, le=365),
) -> dict:
    """Порівняння кімнат: денна серія + avg/min/max по кожній кімнаті.

    Джерело даних для графіка «кімната vs кімната» (температура або вологість).
    Кімнати без відповідного сенсора або без даних не потрапляють у відповідь.
    """
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    out: dict[str, dict] = {}
    sensor_key = "temp_entity" if metric == "temperature" else "humidity_entity"
    for room, cfg in config.load_rooms().items():
        if not cfg.get(sensor_key):
            continue
        points = cache.since(room, metric, since)
        if not points:
            continue
        vals = [v for _, v in points]
        daily: dict[str, list[float]] = {}
        for ts, v in points:
            daily.setdefault(ts[:10], []).append(v)
        out[room] = {
            "avg": round(sum(vals) / len(vals), 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "samples": len(vals),
            "daily": [[d, round(sum(v) / len(v), 2)] for d, v in sorted(daily.items())],
        }
    return {"metric": metric, "days": days, "rooms": out}


@app.get("/api/annotations")
def list_annotations(
    room: str = Query(...),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """User markers (window opened, vacation, ...) for the timeline."""
    if room not in config.load_rooms():
        raise HTTPException(404, f"unknown room: {room}")
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    items = [{"id": i, "ts": ts, "label": label} for i, ts, label in cache.annotations_since(room, since)]
    return {"room": room, "annotations": items}


@app.post("/api/annotations")
def create_annotation(payload: dict) -> dict:
    """Create an annotation: {"room": str, "ts": ISO-8601, "label": str}."""
    room = (payload or {}).get("room")
    ts = (payload or {}).get("ts")
    label = (payload or {}).get("label")
    if not isinstance(room, str) or not isinstance(ts, str) or not isinstance(label, str) or not label.strip():
        raise HTTPException(422, "body must be {\"room\": str, \"ts\": ISO-8601, \"label\": str}")
    if room not in config.load_rooms():
        raise HTTPException(404, f"unknown room: {room}")
    try:
        datetime.fromisoformat(ts)
    except ValueError:
        raise HTTPException(422, "ts must be an ISO-8601 timestamp")
    cache = get_cache()
    ann_id = cache.add_annotation(room, ts, label.strip())
    return {"id": ann_id, "room": room, "ts": ts, "label": label.strip()}


@app.delete("/api/annotations/{ann_id}")
def delete_annotation(ann_id: int) -> dict:
    cache = get_cache()
    if not cache.delete_annotation(ann_id):
        raise HTTPException(404, f"annotation {ann_id} not found")
    return {"status": "ok", "deleted": ann_id}


@app.get("/api/energy")
def energy(
    room: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    price: float | None = Query(None, ge=0),
) -> dict:
    """Hourly/daily kWh consumption for a room + cost at the given (or configured) price."""
    _room_metric(room, "energy")  # validates room + energy sensor presence
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    points = cache.since(room, "energy", since)
    total = round(sum(v for _, v in points), 3)
    p = config.ENERGY_PRICE if price is None else price
    daily: dict[str, float] = {}
    for ts, v in points:
        daily[ts[:10]] = daily.get(ts[:10], 0.0) + v
    return {
        "room": room,
        "days": days,
        "total_kwh": total,
        "price": p,
        "cost": round(total * p, 2),
        "daily": [[d, round(s, 2)] for d, s in sorted(daily.items())],
        "points": points,
    }


@app.get("/api/discover")
def discover_entities() -> dict:
    """List climate sensors from HA grouped by area + a suggested room mapping."""
    if config.DEMO:
        raw = discover.demo_states(config.load_rooms())
    else:
        raw = ha_client.fetch_states_raw()
    sensors = discover.parse_sensors(raw)
    return {
        "demo": config.DEMO,
        "sensors": sensors,
        "suggested_rooms": discover.suggest_mapping(sensors, config.load_rooms()),
        "current_rooms": config.load_rooms(),
    }


@app.post("/api/rooms/config")
def save_rooms_config(payload: dict) -> dict:
    """Persist a rooms mapping (from the discovery settings page) to rooms.json."""
    rooms = (payload or {}).get("rooms")
    if not isinstance(rooms, dict) or not rooms:
        raise HTTPException(422, "body must be {\"rooms\": {...}} with at least one room")
    for room, cfg in rooms.items():
        if not isinstance(cfg, dict):
            raise HTTPException(422, f"room {room!r} must be an object")
        if not isinstance(cfg.get("temp_entity"), str) or not isinstance(cfg.get("humidity_entity"), str):
            raise HTTPException(422, f"room {room!r} needs string temp_entity and humidity_entity")
        for key in ("humidity_min", "humidity_max"):
            if key in cfg and not isinstance(cfg[key], (int, float)):
                raise HTTPException(422, f"room {room!r}: {key} must be a number")
        if isinstance(cfg.get("humidity_min"), (int, float)) and isinstance(cfg.get("humidity_max"), (int, float)) \
                and cfg["humidity_min"] >= cfg["humidity_max"]:
            raise HTTPException(422, f"room {room!r}: humidity_min must be below humidity_max")
        if "floor" in cfg and not isinstance(cfg["floor"], str):
            raise HTTPException(422, f"room {room!r}: floor must be a string (e.g. \"1st\")")
    path = config.save_rooms(rooms)
    return {"status": "ok", "rooms": rooms, "path": str(path)}


# ---------- Data safety: one-click full export + confirmed wipe ----------

@app.get("/api/export/all")
def export_all(format: str = Query("json", pattern="^(json|csv)$")) -> Response:
    """One-click export of ALL local data: readings + annotations (JSON or CSV)."""
    cache = get_cache()
    exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    if format == "json":
        readings = cache.all_readings()
        annotations = [
            {"id": i, "room": room, "ts": ts, "label": label}
            for i, room, ts, label in cache.all_annotations()
        ]
        payload = {
            "app": "climate-canvas",
            "version": app.version,
            "exported_at": exported_at,
            "readings": [{"room": r, "metric": m, "ts": ts, "value": v} for r, m, ts, v in readings],
            "annotations": annotations,
        }
        stamp = exported_at[:10]
        return Response(
            json.dumps(payload, ensure_ascii=False, indent=1),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="climate-canvas-all-{stamp}.json"'},
        )
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(["room", "metric", "ts", "value"])
    for room, metric, ts, value in cache.all_readings():
        writer.writerow([room, metric, ts, value])
    buf.seek(0)
    stamp = exported_at[:10]
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="climate-canvas-all-{stamp}.csv"'},
    )


@app.delete("/api/data")
def wipe_data(confirm: str = Query("", description='must be exactly "DELETE"')) -> dict:
    """Delete ALL local readings and annotations.

    The UI shows a warning first; the request itself must carry
    ?confirm=DELETE so no accidental single call destroys the history.
    """
    if confirm != "DELETE":
        raise HTTPException(422, 'safety: pass ?confirm=DELETE to erase all data')
    deleted = get_cache().wipe()
    return {"status": "ok", "deleted_readings": deleted}


@app.get("/api/export/csv")
def export_csv(
    room: str = Query(...),
    metric: str = Query("temperature", pattern="^(temperature|humidity|co2|voc)$"),
    days: int = Query(7, ge=1, le=365),
) -> StreamingResponse:
    """Download raw cached readings as CSV (Excel/LibreOffice friendly)."""
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    points = cache.since(room, metric, since)

    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(["ts", metric])
    for ts, value in points:
        writer.writerow([ts, value])
    buf.seek(0)
    filename = f"{room.lower().replace(' ', '_')}_{metric}_{days}d.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/report")
def report_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "report.html")


@app.get("/settings")
def settings_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "settings.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
