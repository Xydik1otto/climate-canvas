"""FastAPI application and JSON API for the dashboard."""
from __future__ import annotations

import csv
import io
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import cache as cache_mod
from . import climate, config, demo_data, discover, ha_client, openmeteo, sync

_cache: cache_mod.Cache | None = None
_pull_thread: threading.Thread | None = None


def get_cache() -> cache_mod.Cache:
    global _cache
    if _cache is None:
        _cache = cache_mod.Cache(config.DB_PATH)
        if config.DEMO:
            demo_data.seed_cache(_cache)
        else:
            sync.pull_once(_cache, config.load_rooms())
    return _cache


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup/shutdown via lifespan (replaces deprecated on_event)."""
    global _pull_thread
    get_cache()
    _pull_thread = sync.start_hourly_pull(_cache, config.load_rooms)
    yield


app = FastAPI(title="climate-canvas", version="0.4.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "demo": config.DEMO}


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
        out = {**extra, "comfort": [config.COMFORT_MIN, config.COMFORT_MAX]}
        if t is not None and h is not None:
            out["dew_point"] = climate.dew_point(t, h)
            out["mold_risk"] = climate.mold_risk(t, h)
        else:
            out["dew_point"] = None
            out["mold_risk"] = None
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


@app.get("/api/timeline")
def timeline(
    room: str = Query(...),
    metric: str = Query("temperature", pattern="^(temperature|humidity|co2|voc)$"),
    days: int = Query(7, ge=1, le=365),
) -> dict:
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    points = cache.since(room, metric, since)
    series = cache_mod.hourly_mean(points)
    return {"room": room, "metric": metric, "days": days, "points": series}


HEAT_METRICS = r"^(temperature|humidity|co2|voc|dew_point|mold_risk)$"


def _dew_or_risk_points(cache: cache_mod.Cache, room: str, since: str, metric: str) -> list[tuple[str, float]]:
    """Join cached temperature+humidity hourly means and derive dew point / mold risk."""
    tpts = cache_mod.hourly_mean(cache.since(room, "temperature", since))
    hpts = dict(cache_mod.hourly_mean(cache.since(room, "humidity", since)))
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
    points = cache.since(room, metric, since)
    return cache_mod.heatmap_matrix(points, days)


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
    path = config.save_rooms(rooms)
    return {"status": "ok", "rooms": rooms, "path": str(path)}


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
