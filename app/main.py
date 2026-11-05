"""FastAPI application and JSON API for the dashboard."""
from __future__ import annotations

import csv
import io
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import cache as cache_mod
from . import config, demo_data, discover, ha_client, sync

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


app = FastAPI(title="climate-canvas", version="0.1.0-alpha", lifespan=lifespan)


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
    if config.DEMO:
        now = datetime.now(timezone.utc)
        for room in rooms_cfg:
            out[room] = {**demo_data.current_state(room, now), "comfort": [config.COMFORT_MIN, config.COMFORT_MAX]}
    else:
        try:
            states = ha_client.fetch_states()
        except Exception:
            states = {}
        for room, cfg in rooms_cfg.items():
            t = (states.get(cfg["temp_entity"]) or {}).get("temperature")
            h = (states.get(cfg["humidity_entity"]) or {}).get("humidity")
            out[room] = {
                "temperature": t,
                "humidity": h,
                "comfort": [config.COMFORT_MIN, config.COMFORT_MAX],
            }
    return {"rooms": out, "demo": config.DEMO}


@app.get("/api/timeline")
def timeline(
    room: str = Query(...),
    metric: str = Query("temperature", pattern="^(temperature|humidity)$"),
    days: int = Query(7, ge=1, le=365),
) -> dict:
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    points = cache.since(room, metric, since)
    series = cache_mod.hourly_mean(points)
    return {"room": room, "metric": metric, "days": days, "points": series}


@app.get("/api/heatmap")
def heatmap(
    room: str = Query(...),
    metric: str = Query("temperature", pattern="^(temperature|humidity)$"),
    days: int = Query(90, ge=1, le=365),
) -> dict:
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = cache_mod.hours_ago_iso(days * 24)
    points = cache.since(room, metric, since)
    return cache_mod.heatmap_matrix(points, days)


@app.get("/api/seasons")
def seasons(
    room: str = Query(...),
    metric: str = Query("temperature", pattern="^(temperature|humidity)$"),
    month: int = Query(1, ge=1, le=12),
) -> dict:
    _room_metric(room, metric)  # validates room name
    cache = get_cache()
    since = "1970-01-01T00:00:00+00:00"
    points = [(ts, v) for ts, v in cache.since(room, metric, since) if int(ts[5:7]) == month]
    return {"room": room, "metric": metric, "month": month, "by_year": cache_mod.seasonal_means(points)}


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
    metric: str = Query("temperature", pattern="^(temperature|humidity)$"),
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


@app.get("/settings")
def settings_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "settings.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
