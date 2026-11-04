"""Tests for Home Assistant API response parsing."""
from app.ha_client import parse_history, parse_states


def test_parse_states_extracts_temp_and_humidity(states_fixture):
    out = parse_states(states_fixture)
    assert out["sensor.living_room_temp"] == {"temperature": 22.4}
    assert out["sensor.living_room_hum"] == {"humidity": 47.2}
    assert out["sensor.bedroom_temp"] == {"temperature": 19.8}


def test_parse_states_skips_non_numeric_and_irrelevant(states_fixture):
    out = parse_states(states_fixture)
    # "unavailable" state must not crash parsing
    assert out["sensor.bedroom_temp_broken"]["temperature"] is None
    # watt / binary_sensor entities are not climate metrics
    assert "sensor.kitchen_power" not in out
    assert "binary_sensor.door" not in out


def test_parse_history_flattens_and_filters(history_fixture):
    readings = parse_history(history_fixture)
    # power entity (W) excluded; unavailable excluded
    entities = {r["entity_id"] for r in readings}
    assert "sensor.kitchen_power" not in entities
    temps = [r for r in readings if r["metric"] == "temperature"]
    hums = [r for r in readings if r["metric"] == "humidity"]
    assert len(temps) == 3  # unavailable filtered out
    assert len(hums) == 2
    assert temps[0] == {
        "entity_id": "sensor.living_room_temp",
        "ts": "2026-01-10T10:15:00+00:00",
        "metric": "temperature",
        "value": 21.0,
    }


def test_parse_history_empty_and_missing_ts():
    assert parse_history([]) == []
    assert parse_history([[{"entity_id": "sensor.x", "state": "21.0", "attributes": {"unit_of_measurement": "°C"}}]]) == []
