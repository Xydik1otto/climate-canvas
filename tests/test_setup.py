"""Tests for the Home Assistant setup wizard (URL + token saved in config)."""
import json

from app import config, ha_client


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else []

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._payload


def test_save_setup_persists_to_settings_json(client, tmp_path):
    r = client.post("/api/setup", json={"url": "http://ha.local:8123", "token": "secret-token-1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # base URL is normalized to the REST API root
    assert body["url"] == "http://ha.local:8123/api"
    assert body["token_hint"].endswith("1234")
    saved = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert saved["hass_url"] == "http://ha.local:8123/api"
    assert saved["hass_token"] == "secret-token-1234"


def test_get_setup_never_returns_token(client, tmp_path):
    client.post("/api/setup", json={"url": "http://ha.local:8123", "token": "super-secret-value"})
    r = client.get("/api/setup")
    assert r.status_code == 200
    text = r.text
    assert "super-secret-value" not in text
    data = r.json()
    assert data["token_set"] is True
    assert data["token_hint"].endswith("alue")
    assert data["url"].endswith("/api")


def test_setup_rejects_missing_token(client):
    r = client.post("/api/setup", json={"url": "http://ha.local:8123", "token": "  "})
    assert r.status_code == 422


def test_setup_rejects_bad_url(client):
    r = client.post("/api/setup", json={"url": "ha.local:8123", "token": "t"})
    assert r.status_code == 422


def test_setup_test_connection_ok(client, monkeypatch):
    payload = [
        {"entity_id": "sensor.a", "state": "1", "attributes": {}},
        {"entity_id": "binary_sensor.b", "state": "on", "attributes": {}},
        {"entity_id": "sensor.c", "state": "2", "attributes": {}},
    ]
    calls = {}

    def fake_get(url, headers=None, timeout=None):
        calls["url"], calls["headers"] = url, headers
        return FakeResponse(200, payload)

    monkeypatch.setattr(ha_client.httpx, "get", fake_get)
    r = client.post("/api/setup/test", json={"url": "http://ha.local:8123", "token": "tok"})
    assert r.status_code == 200
    data = r.json()
    assert data == {"ok": True, "status": 200, "sensors": 2}
    assert calls["url"] == "http://ha.local:8123/api/states"
    assert calls["headers"]["Authorization"] == "Bearer tok"


def test_setup_test_connection_failure_is_reported_not_raised(client, monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        raise ConnectionError("boom: no route to host")

    monkeypatch.setattr(ha_client.httpx, "get", fake_get)
    r = client.post("/api/setup/test", json={"url": "http://ha.local:8123", "token": "tok"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert "boom" in data["error"]


def test_setup_test_uses_saved_config_when_body_empty(client, tmp_path, monkeypatch):
    client.post("/api/setup", json={"url": "http://saved.local:8123", "token": "saved-token"})
    calls = {}

    def fake_get(url, headers=None, timeout=None):
        calls["url"] = url
        return FakeResponse(200, [])

    monkeypatch.setattr(ha_client.httpx, "get", fake_get)
    r = client.post("/api/setup/test", json={})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert calls["url"] == "http://saved.local:8123/api/states"


def test_normalize_hass_url_variants():
    assert config.normalize_hass_url("http://ha:8123") == "http://ha:8123/api"
    assert config.normalize_hass_url("http://ha:8123/") == "http://ha:8123/api"
    assert config.normalize_hass_url("http://supervisor/core/api") == "http://supervisor/core/api"
    assert config.normalize_hass_url("  http://ha:8123  ") == "http://ha:8123/api"


def test_hass_url_token_prefer_settings_over_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_ENV_HASS_TOKEN", "env-token")
    monkeypatch.setattr(config, "_ENV_HASS_URL", "http://env-host/api")
    config.save_settings({"hass_url": "http://wizard-host/api", "hass_token": "wizard-token"}, path=tmp_path / "s.json")
    assert config.hass_url(tmp_path / "s.json") == "http://wizard-host/api"
    assert config.hass_token(tmp_path / "s.json") == "wizard-token"
    assert config.hass_url(tmp_path / "missing.json") == "http://env-host/api"
    assert config.hass_token(tmp_path / "missing.json") == "env-token"
    # demo mode: token present -> demo off
    assert config.demo_mode(tmp_path / "s.json") is False
    assert config.demo_mode(tmp_path / "missing.json") is False


def test_corrupt_settings_file_falls_back_to_env(tmp_path, monkeypatch):
    p = tmp_path / "settings.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(config, "_ENV_HASS_TOKEN", "env-token")
    assert config.load_settings(p) == {}
    assert config.hass_token(p) == "env-token"
