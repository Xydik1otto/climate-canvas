"""Deterministic synthetic climate data (demo mode).

Same (room, day) input always produces the same hourly series, so tests and
screenshots are reproducible. The generator models a plausible home:
warmer during the day, cooler at night, humidity inversely correlated,
each room with its own offset and inertia.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from . import config

HOURLY_DAYS = 90  # demo history depth


@lru_cache(maxsize=512)
def _room_profile(room: str) -> tuple[float, float]:
    """Stable per-room (temp offset, humidity offset) derived from the name."""
    h = sum(ord(c) for c in room)
    return ((h % 30) / 10.0 - 1.5, (h % 17) / 2.0 + 30.0)


@lru_cache(maxsize=8192)
def _day_noise(room: str, day: str) -> tuple[float, float, float, float, float]:
    """Pseudo-noise for one (room, day), all metrics in one cached draw.

    Draws the same uniform() values, from the same seeds, in the same order
    as the previous per-metric `random.Random(...)` construction — so the
    generated series is bit-identical, just without re-seeding 5 Randoms
    per hour (the former #1 hot spot, ~43% of seed time).
    """
    return (
        random.Random(f"{room}|{day}").uniform(-0.8, 0.8),
        random.Random(f"{room}|{day}|h").uniform(-2.0, 2.0),
        random.Random(f"{room}|{day}|e").uniform(-0.12, 0.12),
        random.Random(f"{room}|{day}|c").uniform(-40.0, 40.0),
        random.Random(f"{room}|{day}|v").uniform(-15.0, 15.0),
    )


def hour_value(room: str, ts: datetime, metric: str) -> float:
    """Synthetic value for one room/hour, deterministic in (room, ts)."""
    temp_off, hum_off = _room_profile(room)
    # Seasonal component: colder in winter (Jan), warmer in summer (Jul).
    doy = ts.timetuple().tm_yday
    season = 4.0 * math.sin(2 * math.pi * (doy - 105) / 365.0)
    # Diurnal component: peak at 15:00, trough at 03:00.
    diurnal = 2.5 * math.sin(2 * math.pi * (ts.hour - 9) / 24.0)
    # Pseudo-noise seeded by (room, day) — stable within a day (cached).
    noise, hum_noise, e_noise, c_noise, v_noise = _day_noise(room, ts.date().isoformat())
    if metric == "temperature":
        return round(21.0 + temp_off + season + diurnal + noise, 2)
    hum_diurnal = -6.0 * math.sin(2 * math.pi * (ts.hour - 9) / 24.0)
    if metric == "humidity":
        return round(45.0 + hum_off + hum_diurnal + hum_noise, 2)
    if metric == "energy":
        # Hourly consumption: evening cooking peak, morning bump, winter heating.
        base = 0.35
        if 18 <= ts.hour < 22:
            base += 0.9
        elif 7 <= ts.hour < 9:
            base += 0.3
        heating = 0.35 * max(0.0, -season) / 4.0  # more kWh in cold months
        return round(max(0.05, base + heating + e_noise), 3)
    if metric == "co2":
        # Indoor CO2: fresh 450 ppm baseline, people home in the evening.
        base = 450.0
        if 18 <= ts.hour < 23:
            base += 350.0
        elif 7 <= ts.hour < 9:
            base += 150.0
        return round(max(400.0, base + c_noise), 1)
    if metric == "voc":
        # VOC in ppb, loosely tracking CO2 activity.
        base = 110.0 + (60.0 if 18 <= ts.hour < 23 else 0.0)
        return round(max(50.0, base + v_noise), 1)
    raise ValueError(f"unknown metric: {metric}")


def generate_hours(room: str, hours: int = HOURLY_DAYS * 24, end: datetime | None = None) -> list[dict]:
    """Hourly readings for the last `hours` hours, oldest first."""
    end = end or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    out = []
    for i in range(hours, 0, -1):
        ts = end - timedelta(hours=i)
        ts_iso = ts.strftime("%Y-%m-%dT%H:00:00+00:00")
        for metric in ("temperature", "humidity", "energy", "co2", "voc"):
            out.append({"entity_id": room, "ts": ts_iso, "metric": metric, "value": hour_value(room, ts, metric)})
    return out


def outdoor_hour(ts: datetime) -> float:
    """Deterministic synthetic OUTDOOR temperature for one hour (demo mode).

    Wider swings than indoors: stronger seasonality and day/night amplitude.
    """
    doy = ts.timetuple().tm_yday
    season = 9.0 * math.sin(2 * math.pi * (doy - 105) / 365.0)
    diurnal = 4.0 * math.sin(2 * math.pi * (ts.hour - 9) / 24.0)
    noise = _outdoor_noise(ts.date().isoformat(), ts.hour // 6)
    return round(11.0 + season + diurnal + noise, 2)


@lru_cache(maxsize=4096)
def _outdoor_noise(day: str, bucket: int) -> float:
    return random.Random(f"outdoor|{day}|{bucket}").uniform(-1.5, 1.5)


def current_state(room: str, now: datetime | None = None) -> dict[str, float]:
    now = now or datetime.now(timezone.utc)
    h0 = now.replace(minute=0, second=0, microsecond=0)
    return {
        "temperature": hour_value(room, h0, "temperature"),
        "humidity": hour_value(room, h0, "humidity"),
        "co2": hour_value(room, h0, "co2"),
        "voc": hour_value(room, h0, "voc"),
    }


def seed_cache(db, rooms: dict[str, dict] | None = None, days: int = HOURLY_DAYS) -> None:
    """Fill the SQLite cache with demo history (idempotent per day)."""
    rooms = rooms or config.load_rooms()
    now = datetime.now(timezone.utc)
    rows: list[tuple[str, str, str, float]] = []
    for room in rooms:
        for rd in generate_hours(room, hours=days * 24, end=now):
            rows.append((room, rd["metric"], rd["ts"], rd["value"]))
    db.add_readings(rows)  # one executemany instead of 43k+ single INSERTs
