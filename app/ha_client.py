"""Home Assistant REST API client + response parsing.

Parsing functions are pure and unit-tested against recorded fixtures.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from . import config


def parse_states(payload: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    """Parse a HA /api/states response into {entity_id: {metric: value}}.

    Only temperature/humidity sensors with numeric states are kept.
    """
    out: dict[str, dict[str, float | None]] = {}
    for item in payload or []:
        entity_id = item.get("entity_id", "")
        if not entity_id.startswith("sensor."):
            continue
        try:
            value: float | None = float(item.get("state"))
        except (TypeError, ValueError):
            value = None
        attrs = item.get("attributes", {}) or {}
        unit = attrs.get("unit_of_measurement", "")
        if "°C" in unit or unit == "°C":
            metric = "temperature"
        elif unit == "%":
            metric = "humidity"
        elif unit == "kWh":
            metric = "energy"
        elif unit == "ppm":
            metric = "co2"
        elif unit == "ppb":
            metric = "voc"
        else:
            continue
        entry = out.setdefault(entity_id, {})
        entry[metric] = value
    return out


def parse_history(payload: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Parse a HA /api/history/period response into flat readings.

    Returns a list of {"entity_id", "ts" (ISO-8601 UTC), "metric", "value"}.
    Each inner list is the state timeline of one entity; we keep every state
    with a numeric value and its last_updated timestamp.
    """
    readings: list[dict[str, Any]] = []
    for entity_states in payload or []:
        if not entity_states:
            continue
        entity_id = entity_states[0].get("entity_id", "")
        unit = (entity_states[0].get("attributes", {}) or {}).get("unit_of_measurement", "")
        if "°C" in unit or unit == "°C":
            metric = "temperature"
        elif unit == "%":
            metric = "humidity"
        elif unit == "kWh":
            metric = "energy"
        elif unit == "ppm":
            metric = "co2"
        elif unit == "ppb":
            metric = "voc"
        else:
            continue
        for st in entity_states:
            try:
                value = float(st.get("state"))
            except (TypeError, ValueError):
                continue
            ts = st.get("last_updated") or st.get("last_changed")
            if not ts:
                continue
            readings.append({"entity_id": entity_id, "ts": ts, "metric": metric, "value": value})
    return readings


def history_period_url(now: datetime, hours: int = 24, entity_ids: list[str] | None = None) -> str:
    """Build the /api/history/period URL for the last `hours` hours."""
    start = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    url = f"{config.HASS_URL}/history/period/{start}"
    if entity_ids:
        from urllib.parse import urlencode

        url += "?" + urlencode({"filter_entity_id": ",".join(entity_ids), "minimal_response": ""})
    return url


def fetch_states(timeout: float = 10.0) -> dict[str, dict[str, float | None]]:
    """Fetch current states from HA (returns parsed sensor values)."""
    headers = {"Authorization": f"Bearer {config.HASS_TOKEN}"}
    resp = httpx.get(f"{config.HASS_URL}/states", headers=headers, timeout=timeout)
    resp.raise_for_status()
    return parse_states(resp.json())


def fetch_states_raw(timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch the full /api/states payload (used by sensor auto-discovery)."""
    headers = {"Authorization": f"Bearer {config.HASS_TOKEN}"}
    resp = httpx.get(f"{config.HASS_URL}/states", headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_history(entity_ids: list[str], hours: int = 24, timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch recent history for the given entities from HA."""
    headers = {"Authorization": f"Bearer {config.HASS_TOKEN}"}
    url = history_period_url(datetime.now(timezone.utc), hours=hours, entity_ids=entity_ids)
    resp = httpx.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return parse_history(resp.json())
