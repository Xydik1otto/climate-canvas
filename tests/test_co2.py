"""Tests for CO2 (ppm) and VOC (ppb) sensor support."""
from app import config, demo_data, ha_client


def test_parse_states_ppm_and_ppb():
    payload = [
        {"entity_id": "sensor.living_co2", "state": "612", "attributes": {"unit_of_measurement": "ppm"}},
        {"entity_id": "sensor.living_voc", "state": "128", "attributes": {"unit_of_measurement": "ppb"}},
        {"entity_id": "sensor.other", "state": "5", "attributes": {"unit_of_measurement": "m/s"}},
    ]
    out = ha_client.parse_states(payload)
    assert out["sensor.living_co2"] == {"co2": 612.0}
    assert out["sensor.living_voc"] == {"voc": 128.0}
    assert "sensor.other" not in out


def test_parse_history_co2():
    payload = [[
        {"entity_id": "sensor.living_co2", "state": "500", "attributes": {"unit_of_measurement": "ppm"},
         "last_updated": "2026-01-10T10:00:00+00:00"},
        {"entity_id": "sensor.living_co2", "state": "800", "attributes": {"unit_of_measurement": "ppm"},
         "last_updated": "2026-01-10T11:00:00+00:00"},
    ]]
    readings = ha_client.parse_history(payload)
    assert [r["value"] for r in readings] == [500.0, 800.0]
    assert all(r["metric"] == "co2" for r in readings)


def test_demo_co2_voc_deterministic_and_plausible():
    from datetime import datetime, timezone
    ts = datetime(2026, 1, 15, 20, 0, tzinfo=timezone.utc)
    co2 = demo_data.hour_value("Bedroom", ts, "co2")
    voc = demo_data.hour_value("Bedroom", ts, "voc")
    assert co2 == demo_data.hour_value("Bedroom", ts, "co2")
    assert 400.0 <= co2 <= 1500.0
    assert 50.0 <= voc <= 500.0
    # evening occupancy raises CO2 vs night
    night = demo_data.hour_value("Bedroom", ts.replace(hour=3), "co2")
    assert co2 > night


def test_timeline_co2_in_demo(client):
    r = client.get("/api/timeline", params={"room": "Living Room", "metric": "co2", "days": 1})
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) == 24
    assert all(400.0 <= v <= 1500.0 for _, v in points)


def test_timeline_voc_in_demo(client):
    r = client.get("/api/timeline", params={"room": "Office", "metric": "voc", "days": 1})
    assert r.status_code == 200
    assert all(50.0 <= v <= 500.0 for _, v in r.json()["points"])


def test_rooms_includes_co2_voc(client):
    r = client.get("/api/rooms")
    st = r.json()["rooms"]["Living Room"]
    assert 400.0 <= st["co2"] <= 1500.0
    assert 50.0 <= st["voc"] <= 500.0


def test_room_without_co2_sensor_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    config.save_rooms({"Closet": {"temp_entity": "sensor.c", "humidity_entity": "sensor.h"}})
    r = client.get("/api/timeline", params={"room": "Closet", "metric": "co2", "days": 1})
    assert r.status_code == 404
    assert "no co2 sensor" in r.json()["detail"]
