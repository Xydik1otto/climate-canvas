"""Групи/поверхи кімнат: `floor` у rooms.json + /api/floors."""
from app import floors


def test_group_by_floor_explicit_and_default():
    rooms = {
        "Вітальня": {"temp_entity": "t", "humidity_entity": "h", "floor": "1"},
        "Кухня": {"temp_entity": "t", "humidity_entity": "h", "floor": "1"},
        "Спальня": {"temp_entity": "t", "humidity_entity": "h", "floor": "2"},
        "Гараж": {"temp_entity": "t", "humidity_entity": "h"},  # без поверху
        "Порожньо": {"temp_entity": "t", "humidity_entity": "h", "floor": "  "},
    }
    groups = floors.group_by_floor(rooms)
    assert groups["1"] == ["Вітальня", "Кухня"]
    assert groups["2"] == ["Спальня"]
    assert floors.UNASSIGNED in groups
    assert set(groups[floors.UNASSIGNED]) == {"Гараж", "Порожньо"}


def test_floor_summary_averages_skip_missing():
    rooms = {
        "A": {"floor": "1"},
        "B": {"floor": "1"},
        "C": {},  # "none"
    }
    current = {
        "A": {"temperature": 20.0, "humidity": 40.0},
        "B": {"temperature": 22.0, "humidity": None},
    }
    summary = floors.floor_summary(rooms, current)
    assert summary["1"]["rooms"] == ["A", "B"]
    assert summary["1"]["avg_temperature"] == 21.0
    assert summary["1"]["avg_humidity"] == 40.0  # None пропускається
    assert summary[floors.UNASSIGNED]["rooms"] == ["C"]
    assert summary[floors.UNASSIGNED]["avg_temperature"] is None


def test_api_floors_demo(client):
    from app import config

    r = client.get("/api/floors")
    assert r.status_code == 200
    data = r.json()
    assert data["demo"] is True
    # без `floor` у rooms.json усе потрапляє в групу "none"
    all_rooms = data["floors"][floors.UNASSIGNED]["rooms"]
    assert set(all_rooms) == set(config.DEFAULT_ROOMS)
    assert isinstance(data["floors"][floors.UNASSIGNED]["avg_temperature"], float)


def test_api_rooms_expose_floor(client):
    rooms = client.get("/api/rooms").json()["rooms"]
    for st in rooms.values():
        assert st["floor"] is None  # у демо-конфігу поверхи не задані


def test_api_rooms_config_accepts_floor(client, tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    r = client.post("/api/rooms/config", json={"rooms": {
        "Вітальня": {"temp_entity": "s.t", "humidity_entity": "s.h", "floor": "1"},
    }})
    assert r.status_code == 200
    assert r.json()["rooms"]["Вітальня"]["floor"] == "1"


def test_api_rooms_config_rejects_non_string_floor(client, tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    r = client.post("/api/rooms/config", json={"rooms": {
        "Вітальня": {"temp_entity": "s.t", "humidity_entity": "s.h", "floor": 1},
    }})
    assert r.status_code == 422
    assert "floor" in r.json()["detail"]
