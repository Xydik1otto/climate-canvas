"""Групи кімнат за поверхами: необов'язковий ключ `floor` у rooms.json.

Кімната без `floor` (або з порожнім рядком) потрапляє в групу "none",
щоб API залишався стабільним для фронтенду.
"""
from __future__ import annotations

from . import config

UNASSIGNED = "none"


def group_by_floor(rooms: dict) -> dict[str, list[str]]:
    """Згрупувати імена кімнат за ключем `floor` (порядок збереження)."""
    out: dict[str, list[str]] = {}
    for room, cfg in rooms.items():
        floor = cfg.get("floor") if isinstance(cfg, dict) else None
        key = floor.strip() if isinstance(floor, str) and floor.strip() else UNASSIGNED
        out.setdefault(key, []).append(room)
    return out


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def floor_summary(rooms: dict, current: dict[str, dict]) -> dict[str, dict]:
    """Підсумок по поверхах: кімнати + середні поточні температура/вологість.

    `current` — {кімната: {"temperature": float|None, "humidity": float|None}}.
    """
    out: dict[str, dict] = {}
    for floor, members in group_by_floor(rooms).items():
        temps = [current[r]["temperature"] for r in members
                 if r in current and current[r].get("temperature") is not None]
        hums = [current[r]["humidity"] for r in members
                if r in current and current[r].get("humidity") is not None]
        out[floor] = {
            "rooms": members,
            "avg_temperature": _mean(temps),
            "avg_humidity": _mean(hums),
        }
    return out


def current_room_values() -> dict[str, dict]:
    """Поточні темп/вологість по кімнатах (demo чи HA) — спільно з /api/rooms."""
    from . import demo_data, ha_client

    rooms_cfg = config.load_rooms()
    if config.DEMO:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        return {room: demo_data.current_state(room, now) for room in rooms_cfg}
    try:
        states = ha_client.fetch_states()
    except Exception:
        states = {}
    out = {}
    for room, cfg in rooms_cfg.items():
        t = (states.get(cfg["temp_entity"]) or {}).get("temperature")
        h = (states.get(cfg["humidity_entity"]) or {}).get("humidity")
        out[room] = {"temperature": t, "humidity": h}
    return out
