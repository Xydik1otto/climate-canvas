"""Sensor auto-discovery: parse HA /api/states and suggest a room mapping.

Pure functions only — everything here is unit-tested against fixtures.
"""
from __future__ import annotations

from typing import Any


def parse_sensors(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract climate-relevant sensor.* entities with their area.

    Returns a list of {entity_id, name, area, metric, unit, value}.
    Area comes from attributes.area_id when HA provides it, otherwise it is
    guessed from the first token of the friendly name (e.g.
    "Bedroom Temperature" -> "bedroom"), falling back to "unknown".
    """
    sensors: list[dict[str, Any]] = []
    for item in states or []:
        entity_id = item.get("entity_id", "")
        if not entity_id.startswith("sensor."):
            continue
        attrs = item.get("attributes", {}) or {}
        unit = attrs.get("unit_of_measurement", "")
        if "°C" in unit:
            metric = "temperature"
        elif unit == "%":
            metric = "humidity"
        elif unit == "kWh":
            metric = "energy"
        else:
            continue
        try:
            value: float | None = float(item.get("state"))
        except (TypeError, ValueError):
            value = None
        friendly = attrs.get("friendly_name") or ""
        sensors.append(
            {
                "entity_id": entity_id,
                "name": friendly or entity_id.removeprefix("sensor.").replace("_", " ").title(),
                "area": attrs.get("area_id") or _area_from_name(friendly),
                "metric": metric,
                "unit": unit,
                "value": value,
            }
        )
    return sensors


def _area_from_name(friendly_name: str) -> str:
    """Guess an area slug from the first word of a friendly name."""
    first = friendly_name.strip().split(" ")[0] if friendly_name.strip() else ""
    return first.lower() or "unknown"


def suggest_mapping(sensors: list[dict[str, Any]], current_rooms: dict[str, dict]) -> dict[str, dict]:
    """Group sensors by area and propose a rooms.json-style mapping.

    For each area the first temperature sensor becomes temp_entity and the
    first humidity sensor humidity_entity. Rooms that already exist in
    current_rooms keep their extra keys (e.g. co2_entity) when the entity
    matches the suggestion.
    """
    by_area: dict[str, list[dict]] = {}
    for s in sensors:
        by_area.setdefault(s["area"], []).append(s)

    suggested: dict[str, dict] = {}
    for area, items in sorted(by_area.items()):
        if area == "unknown":
            continue
        temp = next((s["entity_id"] for s in items if s["metric"] == "temperature"), None)
        hum = next((s["entity_id"] for s in items if s["metric"] == "humidity"), None)
        if not (temp or hum):
            continue
        room_name = area.replace("_", " ").title()
        entry: dict[str, str] = {}
        if temp:
            entry["temp_entity"] = temp
        if hum:
            entry["humidity_entity"] = hum
        # Preserve non-climate extras (energy_entity, co2_entity, ...) from an
        # existing config when the primary entities match.
        old = _find_current(current_rooms, room_name, temp, hum)
        if old:
            for key, val in old.items():
                if key not in entry and isinstance(val, str):
                    entry[key] = val
        suggested[room_name] = entry
    return suggested


def _find_current(current_rooms: dict, room_name: str, temp: str | None, hum: str | None) -> dict | None:
    """Match a suggested room against current config (by name or entities)."""
    cfg = current_rooms.get(room_name)
    if cfg:
        return cfg
    for cfg in current_rooms.values():
        if (temp and cfg.get("temp_entity") == temp) or (hum and cfg.get("humidity_entity") == hum):
            return cfg
    return None


def demo_states(rooms: dict[str, dict]) -> list[dict[str, Any]]:
    """Synthesise an /api/states payload for the configured rooms (demo mode)."""
    out: list[dict[str, Any]] = []
    samples = {"temperature": ("°C", 21.5), "humidity": ("%", 47.0), "energy": ("kWh", 0.5)}
    key_for = {"temperature": "temp_entity", "humidity": "humidity_entity", "energy": "energy_entity"}
    for room, cfg in rooms.items():
        area = room.lower().replace(" ", "_")
        for metric, (unit, value) in samples.items():
            entity = cfg.get(key_for[metric])
            if not entity:
                continue
            out.append(
                {
                    "entity_id": entity,
                    "state": str(value),
                    "attributes": {
                        "unit_of_measurement": unit,
                        "friendly_name": f"{room} {metric.title()}",
                        "area_id": area,
                    },
                }
            )
    return out
