"""End-to-end API tests in demo mode (no Home Assistant needed)."""
from app import config


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["demo"] is True
    assert data["has_data"] is True  # conftest seeds demo history


def test_rooms_returns_all_rooms_with_comfort(client):
    r = client.get("/api/rooms")
    assert r.status_code == 200
    data = r.json()
    assert data["demo"] is True
    assert set(data["rooms"]) == set(config.DEFAULT_ROOMS)
    for st in data["rooms"].values():
        assert st["comfort"] == [config.COMFORT_MIN, config.COMFORT_MAX]
        assert 10.0 <= st["temperature"] <= 45.0


def test_timeline_7_days_hourly(client):
    r = client.get("/api/timeline", params={"room": "Bedroom", "metric": "temperature", "days": 7})
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) == 7 * 24
    assert all(isinstance(v, float) for _, v in points)


def test_timeline_unknown_room_404(client):
    r = client.get("/api/timeline", params={"room": "Atlantis", "metric": "temperature", "days": 7})
    assert r.status_code == 404


def test_heatmap_returns_matrix(client):
    r = client.get("/api/heatmap", params={"room": "Kitchen", "days": 30})
    assert r.status_code == 200
    m = r.json()
    assert len(m["values"]) == 30
    assert m["hours"] == list(range(24))


def test_seasons_compares_years(client):
    # demo history covers the last 90 days, so query the current month
    from datetime import datetime, timezone

    month = datetime.now(timezone.utc).month
    r = client.get("/api/seasons", params={"room": "Living Room", "month": month})
    assert r.status_code == 200
    by_year = r.json()["by_year"]
    assert len(by_year) >= 1
    assert all(-30.0 <= v <= 45.0 for v in by_year.values())


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Climate Canvas" in r.text
