"""Background hourly pull + cache bootstrap."""
from __future__ import annotations

import logging
import threading
import time as _time

from . import config, ha_client

log = logging.getLogger("climate-canvas")
PULL_INTERVAL = 3600  # seconds


def pull_once(cache, rooms: dict[str, dict]) -> int:
    """Pull the last 24h of history for all configured entities into the cache."""
    entity_map: dict[str, str] = {}
    for room, cfg in rooms.items():
        for key in ("temp_entity", "humidity_entity"):
            ent = cfg.get(key)
            if ent:
                entity_map[ent] = room
    rows = []
    for reading in ha_client.fetch_history(list(entity_map)):
        room = entity_map.get(reading["entity_id"])
        if room:
            rows.append((room, reading["metric"], reading["ts"], reading["value"]))
    if rows:
        cache.add_readings(rows)
    log.info("pulled %d readings from HA", len(rows))
    return len(rows)


def start_hourly_pull(cache, rooms_provider) -> threading.Thread | None:
    """Start a daemon thread that pulls data every hour. Skipped in demo mode."""

    def loop() -> None:
        while True:
            try:
                pull_once(cache, rooms_provider())
            except Exception:  # keep the loop alive on network errors
                log.exception("hourly pull failed")
            _time.sleep(PULL_INTERVAL)

    if config.DEMO:
        return None
    t = threading.Thread(target=loop, daemon=True, name="ha-hourly-pull")
    t.start()
    return t
