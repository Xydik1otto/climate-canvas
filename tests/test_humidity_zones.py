"""Tests for configurable per-room humidity comfort zones."""
from app import config


def test_default_humidity_zone_in_rooms(client):
    data = client.get("/api/rooms").json()
    for st in data["rooms"].values():
        assert st["humidity_comfort"] == [config.HUMIDITY_MIN, config.HUMIDITY_MAX]
        assert 0.0 < st["humidity_comfort"][0] < st["humidity_comfort"][1] <= 100.0


def test_per_room_humidity_zone_roundtrip(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    rooms = {
        "Bedroom": {"temp_entity": "sensor.b_t", "humidity_entity": "sensor.b_h",
                    "humidity_min": 40.0, "humidity_max": 60.0},
        "Kitchen": {"temp_entity": "sensor.k_t", "humidity_entity": "sensor.k_h",
                    "humidity_min": 35.0, "humidity_max": 55.0},
    }
    r = client.post("/api/rooms/config", json={"rooms": rooms})
    assert r.status_code == 200
    assert r.json()["rooms"]["Bedroom"]["humidity_min"] == 40.0

    data = client.get("/api/rooms").json()
    assert data["rooms"]["Bedroom"]["humidity_comfort"] == [40.0, 60.0]
    assert data["rooms"]["Kitchen"]["humidity_comfort"] == [35.0, 55.0]


def test_humidity_zone_partial_override_uses_defaults(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    rooms = {
        "Office": {"temp_entity": "sensor.o_t", "humidity_entity": "sensor.o_h",
                    "humidity_max": 45.0},
    }
    assert client.post("/api/rooms/config", json={"rooms": rooms}).status_code == 200
    data = client.get("/api/rooms").json()
    assert data["rooms"]["Office"]["humidity_comfort"] == [config.HUMIDITY_MIN, 45.0]


def test_humidity_zone_rejects_inverted_range(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    rooms = {"Bath": {"temp_entity": "s.t", "humidity_entity": "s.h",
                       "humidity_min": 60.0, "humidity_max": 40.0}}
    r = client.post("/api/rooms/config", json={"rooms": rooms})
    assert r.status_code == 422
    assert "humidity_min" in r.json()["detail"]


def test_humidity_zone_rejects_non_numeric(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    rooms = {"Bath": {"temp_entity": "s.t", "humidity_entity": "s.h", "humidity_min": "wet"}}
    r = client.post("/api/rooms/config", json={"rooms": rooms})
    assert r.status_code == 422


def test_demo_state_respects_zone_class(client):
    """Room cards expose humidity alongside its zone so the UI can classify it."""
    data = client.get("/api/rooms").json()
    for st in data["rooms"].values():
        lo, hi = st["humidity_comfort"]
        assert lo < st["humidity"] < 100.0
