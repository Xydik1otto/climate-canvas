"""MQTT-інжесція Zigbee2MQTT: парсинг payload, мапінг кімнат, API."""
import json
from datetime import datetime, timezone

import pytest

from app import mqtt_ingest

NOW = datetime(2026, 11, 5, 14, 30, tzinfo=timezone.utc)
NOW_TS = "2026-11-05T14:00:00+00:00"

MAPPING = {"Кухня Сенсор": "Кухня", "Bedroom TZ": "Bedroom"}


def test_parse_message_maps_metrics():
    payload = json.dumps({"temperature": 21.4, "humidity": 48.2, "co2": 610,
                          "carbon_dioxide": 700, "occupancy": True, "battery": 87})
    rows = mqtt_ingest.parse_message("zigbee2mqtt/Кухня Сенсор", payload, MAPPING, now=NOW)
    by_metric = {m: v for _r, m, _t, v in rows}
    rooms = {r for r, _m, _t, _v in rows}
    assert rooms == {"Кухня"}
    assert by_metric == {"temperature": 21.4, "humidity": 48.2, "co2": 610.0}
    # carbon_dioxide — синонім co2, канонічний ключ виграє; усі ts — годинний бакет
    assert all(t == NOW_TS for _r, _m, t, _v in rows)


def test_parse_message_unknown_device_ignored():
    payload = json.dumps({"temperature": 20.0})
    assert mqtt_ingest.parse_message("zigbee2mqtt/Інший пристрій", payload, MAPPING, now=NOW) == []


def test_parse_message_foreign_topic_and_bad_payload():
    assert mqtt_ingest.parse_message("homeassistant/sensor/x", "{}", MAPPING) == []
    assert mqtt_ingest.parse_message("zigbee2mqtt/Кухня Сенсор", "not json", MAPPING) == []
    assert mqtt_ingest.parse_message("zigbee2mqtt/Кухня Сенсор/availability", "online", MAPPING) == []


def test_parse_message_case_insensitive_friendly_name_and_last_seen():
    payload = json.dumps({"temperature": 19.0, "last_seen": "2026-11-05T13:05:44+00:00"})
    rows = mqtt_ingest.parse_message("zigbee2mqtt/bedroom tz", payload, MAPPING, now=NOW)
    assert rows and rows[0][0] == "Bedroom" and rows[0][2] == "2026-11-05T13:00:00+00:00"


def test_ingestor_handle_writes_cache(tmp_path):
    from app import cache as cache_mod

    db = cache_mod.Cache(tmp_path / "c.db")
    ing = mqtt_ingest.MqttIngestor(db, MAPPING)
    payload = json.dumps({"temperature": 22.0, "humidity": 40.0})
    n = ing.handle("zigbee2mqtt/Bedroom TZ", payload)
    assert n == 2
    rows = db.since("Bedroom", "temperature", "2000-01-01T00:00:00+00:00")
    assert len(rows) == 1 and rows[0][1] == 22.0


def test_ingestor_start_requires_paho(tmp_path):
    from app import cache as cache_mod

    ing = mqtt_ingest.MqttIngestor(cache_mod.Cache(tmp_path / "c.db"), MAPPING)
    with pytest.raises(RuntimeError, match="paho-mqtt"):
        ing.start("127.0.0.1")


# ---------- API ----------

def test_mqtt_settings_roundtrip(client):
    r = client.post("/api/mqtt", json={
        "mqtt_enabled": True, "mqtt_host": "mqtt.local", "mqtt_port": 1884,
        "mqtt_rooms": {"Кухня Сенсор": "Kitchen"},
    })
    assert r.status_code == 200
    data = client.get("/api/mqtt").json()
    assert data["enabled"] is True and data["host"] == "mqtt.local" and data["port"] == 1884
    assert data["rooms"] == {"Кухня Сенсор": "Kitchen"}
    assert isinstance(data["paho_installed"], bool)


def test_mqtt_settings_rejects_bad_port_and_rooms(client):
    assert client.post("/api/mqtt", json={"mqtt_port": 99999}).status_code == 422
    assert client.post("/api/mqtt", json={"mqtt_port": "x"}).status_code == 422
    assert client.post("/api/mqtt", json={"mqtt_rooms": {"a": ""}}).status_code == 422
    assert client.post("/api/mqtt", json={}).status_code == 422


def test_mqtt_ingest_endpoint_stores_reading(client, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "SETTINGS_FILE", config.SETTINGS_FILE.parent / "nonexistent.json")
    # спочатку зберігаємо мапінг
    r = client.post("/api/mqtt", json={"mqtt_rooms": {"Bedroom TZ": "Bedroom"}})
    assert r.status_code == 200
    r = client.post("/api/mqtt/ingest", json={
        "topic": "zigbee2mqtt/Bedroom TZ",
        "payload": {"temperature": 23.5, "humidity": 44.0},
    })
    assert r.status_code == 200
    assert r.json()["added"] == 2
    # значення реально в кеші й видно через /api/timeline
    tl = client.get("/api/timeline", params={"room": "Bedroom", "metric": "temperature", "days": 1}).json()
    assert any(v == 23.5 for _, v in tl["points"])


def test_mqtt_ingest_endpoint_rejects_unmapped(client):
    r = client.post("/api/mqtt/ingest", json={
        "topic": "zigbee2mqtt/Nobody", "payload": json.dumps({"temperature": 1.0}),
    })
    assert r.status_code == 422
    assert "nothing ingested" in r.json()["detail"]
