"""FastAPI application and JSON API for the dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import cache as cache_mod
from . import config, demo_data, sync

app = FastAPI(title="climate-canvas", version="0.1.0")

_cache: cache_mod.Cache | None = None


def get_cache() -> cache_mod.Cache:
    global _cache
    if _cache is None:
        _cache = cache_mod.Cache(config.DB_PATH)
        if config.DEMO:
            demo_data.seed_cache(_cache)
        else:
            sync.pull_once(_cache, config.load_rooms())
    return _cache


@app.on_event("startup")
def startup() -> None:
    get_cache()
    sync.start_hourly_pull(_cache, config.load_rooms)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "demo": config.DEMO}


def _room_metric(room: str, metric: str) -> str:
    rooms = config.load_rooms()
    cfg = rooms.get(room)
    if cfg is None:
        raise HTTPException(404, f"unknown room: {room}")
    return cfg["temp_entity"] if metric == "temperature" else cfg["humidity_entity"]


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


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
