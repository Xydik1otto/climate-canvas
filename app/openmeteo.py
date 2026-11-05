"""Open-Meteo client (free public API, no key required).

Parsing functions are pure and unit-tested; the fetchers wrap httpx and never
raise — on network problems they return an empty series so the dashboard
keeps working offline.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from . import config

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def archive_url(lat: float, lon: float, start_date: str, end_date: str) -> str:
    """Hourly temperature history (UTC) for the given inclusive date range."""
    return (
        f"{ARCHIVE_URL}?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        "&hourly=temperature_2m&timezone=UTC"
    )


def forecast_url(lat: float, lon: float, hours: int = 48) -> str:
    """Hourly temperature forecast for the next `hours` hours (UTC)."""
    return (
        f"{FORECAST_URL}?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m&forecast_hours={hours}&timezone=UTC"
    )


def parse_hourly(payload: dict[str, Any]) -> list[tuple[str, float]]:
    """Parse an Open-Meteo hourly response into [(ISO-8601 UTC ts, °C)].

    Missing/None values are dropped; timestamps get a `+00:00` suffix so they
    are directly comparable with cache timestamps.
    """
    hourly = (payload or {}).get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    out: list[tuple[str, float]] = []
    for ts, v in zip(times, temps):
        if v is None:
            continue
        iso = ts if len(ts) > 16 else ts + ":00"
        if not iso.endswith("+00:00"):
            iso += "+00:00"
        out.append((iso, float(v)))
    return out


def fetch_archive(days: int, timeout: float = 20.0) -> list[tuple[str, float]]:
    """Last `days` days of outdoor temperature from the Open-Meteo archive API."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    url = archive_url(config.LATITUDE, config.LONGITUDE, start.isoformat(), end.isoformat())
    try:
        resp = httpx.get(url, timeout=timeout)
        resp.raise_for_status()
        return parse_hourly(resp.json())
    except Exception:
        return []


def fetch_forecast(hours: int = 48, timeout: float = 20.0) -> list[tuple[str, float]]:
    """Next `hours` hours of outdoor temperature forecast from Open-Meteo."""
    url = forecast_url(config.LATITUDE, config.LONGITUDE, hours)
    try:
        resp = httpx.get(url, timeout=timeout)
        resp.raise_for_status()
        return parse_hourly(resp.json())
    except Exception:
        return []
