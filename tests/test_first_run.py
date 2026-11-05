"""Tests for the first-run experience: demo data is opt-in via a UI button."""
import pytest

from app import config, demo_data


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    """TestClient on an empty demo install (no seeded history)."""
    from fastapi.testclient import TestClient

    from app import main

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr(config, "DEMO", True)
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    main._cache = None
    with TestClient(main.app) as c:
        yield c
    main._cache = None


def test_fresh_install_has_empty_cache_no_auto_seed(fresh):
    """A fresh demo install must NOT auto-seed: /api/health reports has_data=False."""
    r = fresh.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["demo"] is True
    assert data["has_data"] is False


def test_demo_seed_endpoint_fills_history(fresh):
    r = fresh.post("/api/demo/seed")
    assert r.status_code == 200
    points = r.json()["points"]
    rooms = len(config.load_rooms())
    assert points == rooms * demo_data.HOURLY_DAYS * 24 * 5  # 5 metrics per hour
    # now the timeline has data
    tl = fresh.get("/api/timeline", params={"room": "Bedroom", "metric": "temperature", "days": 7}).json()
    assert len(tl["points"]) == 7 * 24


def test_demo_seed_is_idempotent(fresh):
    r1 = fresh.post("/api/demo/seed").json()
    r2 = fresh.post("/api/demo/seed").json()
    assert r1["points"] > 0
    assert r2["points"] == 0  # INSERT OR REPLACE: same day -> nothing new


def test_demo_seed_refused_when_ha_configured(fresh, monkeypatch):
    monkeypatch.setattr(config, "DEMO", False)
    r = fresh.post("/api/demo/seed")
    assert r.status_code == 409
    assert "Home Assistant" in r.json()["detail"]


def test_index_serves_first_run_banner_markup(client):
    html = client.get("/").text
    assert 'id="first-run"' in html
    assert 'id="demo-seed-btn"' in html
