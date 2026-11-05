"""Tests for sensor auto-discovery (parsing, mapping, API endpoints)."""
import json

import pytest

from app import config, discover
from tests.conftest import FIXTURES


@pytest.fixture
def discovery_fixture():
    return json.loads((FIXTURES / "states_discovery.json").read_text(encoding="utf-8"))


def test_parse_sensors_groups_by_area(discovery_fixture):
    sensors = discover.parse_sensors(discovery_fixture)
    by_id = {s["entity_id"]: s for s in sensors}
    assert "sensor.kitchen_power" not in by_id
    assert "binary_sensor.door" not in by_id
    assert by_id["sensor.living_room_temp"]["area"] == "living_room"
    assert by_id["sensor.living_room_temp"]["metric"] == "temperature"
    assert by_id["sensor.living_room_hum"]["metric"] == "humidity"


def test_parse_sensors_area_fallback_from_friendly_name(discovery_fixture):
    sensors = discover.parse_sensors(discovery_fixture)
    by_id = {s["entity_id"]: s for s in sensors}
    # no area_id attribute -> guessed from friendly name
    assert by_id["sensor.office_climate"]["area"] == "office"
    # unavailable state parses to value=None, entity still listed
    assert by_id["sensor.broken"]["value"] is None
    assert by_id["sensor.broken"]["area"] == "garage"


def test_suggest_mapping_builds_rooms_config(discovery_fixture):
    sensors = discover.parse_sensors(discovery_fixture)
    suggested = discover.suggest_mapping(sensors, {})
    assert suggested["Living Room"] == {
        "temp_entity": "sensor.living_room_temp",
        "humidity_entity": "sensor.living_room_hum",
    }
    assert suggested["Bedroom"] == {"temp_entity": "sensor.bedroom_temp"}
    assert suggested["Attic"] == {"humidity_entity": "sensor.attic_hum"}


def test_suggest_mapping_preserves_current_extras(discovery_fixture):
    sensors = discover.parse_sensors(discovery_fixture)
    current = {"Living Room": {"temp_entity": "sensor.living_room_temp",
                               "humidity_entity": "sensor.living_room_hum",
                               "energy_entity": "sensor.home_energy"}}
    suggested = discover.suggest_mapping(sensors, current)
    assert suggested["Living Room"]["energy_entity"] == "sensor.home_energy"


def test_discover_endpoint_demo_mode(client):
    r = client.get("/api/discover")
    assert r.status_code == 200
    data = r.json()
    assert data["demo"] is True
    assert len(data["sensors"]) == 2 * len(config.DEFAULT_ROOMS)
    assert data["suggested_rooms"]["Living Room"]["temp_entity"] == "sensor.living_room_temp"
    assert data["current_rooms"] == config.DEFAULT_ROOMS


def test_save_rooms_config_roundtrip(client, tmp_path, monkeypatch):
    target = tmp_path / "rooms.json"
    monkeypatch.setattr(config, "ROOMS_CONFIG", target)
    rooms = {"Вітальня": {"temp_entity": "sensor.a", "humidity_entity": "sensor.b"}}
    r = client.post("/api/rooms/config", json={"rooms": rooms})
    assert r.status_code == 200
    assert json.loads(target.read_text(encoding="utf-8")) == rooms


def test_save_rooms_config_rejects_bad_payload(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    r = client.post("/api/rooms/config", json={"rooms": {}})
    assert r.status_code == 422
    r = client.post("/api/rooms/config", json={"rooms": {"X": {"temp_entity": 1}}})
    assert r.status_code == 422


def test_settings_page_served(client):
    r = client.get("/settings")
    assert r.status_code == 200
    assert "Налаштування" in r.text
