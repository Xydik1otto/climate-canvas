"""Tests for the energy (kWh) feature: parsing, demo data, API with cost."""
from pathlib import Path

import pytest

from app import config, demo_data, ha_client, sync
from app.cache import Cache


def test_parse_states_kwh_becomes_energy():
    payload = [{"entity_id": "sensor.home_energy", "state": "12.5",
                "attributes": {"unit_of_measurement": "kWh", "friendly_name": "Home Energy"}}]
    out = ha_client.parse_states(payload)
    assert out["sensor.home_energy"] == {"energy": 12.5}


def test_parse_history_kwh_becomes_energy():
    payload = [[
        {"entity_id": "sensor.home_energy", "state": "10.0", "attributes": {"unit_of_measurement": "kWh"}},
        {"entity_id": "sensor.home_energy", "state": "10.4", "attributes": {"unit_of_measurement": "kWh"},
         "last_updated": "2026-01-10T10:00:00+00:00"},
    ]]
    readings = ha_client.parse_history(payload)
    assert len(readings) == 1
    assert readings[0]["metric"] == "energy"
    assert readings[0]["value"] == 10.4


def test_demo_energy_deterministic_and_plausible():
    from datetime import datetime, timezone
    ts = datetime(2026, 1, 15, 19, 0, tzinfo=timezone.utc)
    a = demo_data.hour_value("Kitchen", ts, "energy")
    b = demo_data.hour_value("Kitchen", ts, "energy")
    assert a == b
    assert 0.05 <= a <= 2.5
    # evening cooking peak is higher than 03:00 baseline
    night = demo_data.hour_value("Kitchen", ts.replace(hour=3), "energy")
    assert a > night


def test_sync_maps_energy_entity_to_room(monkeypatch):
    readings = [{"entity_id": "sensor.home_energy", "ts": "2026-01-10T10:00:00+00:00",
                 "metric": "energy", "value": 0.5}]
    monkeypatch.setattr(ha_client, "fetch_history", lambda ids, hours=24: readings)
    cache = Cache(Path(":memory:"))
    rooms = {"Garage": {"energy_entity": "sensor.home_energy"}}
    n = sync.pull_once(cache, rooms)
    assert n == 1
    assert cache.since("Garage", "energy", "1970-01-01T00:00:00+00:00") == [
        ("2026-01-10T10:00:00+00:00", 0.5)
    ]


def test_energy_api_totals_and_cost(client):
    r = client.get("/api/energy", params={"room": "Kitchen", "days": 7, "price": 2.0})
    assert r.status_code == 200
    data = r.json()
    assert data["total_kwh"] > 0
    assert data["price"] == 2.0
    assert data["cost"] == round(data["total_kwh"] * 2.0, 2)
    # a 168h window can spill into an 8th calendar date (partial first day)
    assert 7 <= len(data["daily"]) <= 8
    assert all(0.0 < v < 40.0 for _, v in data["daily"])  # daily kWh sums


def test_energy_api_default_price_from_config(client):
    r = client.get("/api/energy", params={"room": "Office", "days": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["price"] == config.ENERGY_PRICE


def test_energy_api_room_without_energy_sensor_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    # demo seeded DEFAULT_ROOMS (with energy), but a custom config without energy must 404
    config.save_rooms({"Closet": {"temp_entity": "sensor.c", "humidity_entity": "sensor.h"}})
    r = client.get("/api/energy", params={"room": "Closet"})
    assert r.status_code == 404
