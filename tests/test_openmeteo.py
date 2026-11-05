"""Open-Meteo client: URL builders, pure parsing, demo-mode /api/outdoor."""
from app import config, openmeteo


def test_archive_url_contains_coords_and_dates():
    url = openmeteo.archive_url(50.45, 30.52, "2026-11-01", "2026-11-05")
    assert url.startswith("https://archive-api.open-meteo.com/v1/archive?")
    assert "latitude=50.45" in url and "longitude=30.52" in url
    assert "start_date=2026-11-01" in url and "end_date=2026-11-05" in url
    assert "hourly=temperature_2m" in url and "timezone=UTC" in url


def test_parse_hourly_normalizes_timestamps():
    payload = {
        "hourly": {
            "time": ["2026-11-01T00:00", "2026-11-01T01:00", "2026-11-01T02:00"],
            "temperature_2m": [8.1, None, 9.4],
        }
    }
    pts = openmeteo.parse_hourly(payload)
    assert pts == [
        ("2026-11-01T00:00:00+00:00", 8.1),
        ("2026-11-01T02:00:00+00:00", 9.4),
    ]  # None dropped, "+00:00" appended


def test_parse_hourly_handles_empty_payload():
    assert openmeteo.parse_hourly({}) == []
    assert openmeteo.parse_hourly(None) == []


def test_outdoor_endpoint_demo(client):
    r = client.get("/api/outdoor", params={"days": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "demo"
    assert data["location"] == [config.LATITUDE, config.LONGITUDE]
    assert len(data["points"]) == 3 * 24 + 1  # inclusive hourly range
    for ts, v in data["points"]:
        assert ts.endswith("+00:00")
        assert -40.0 <= v <= 45.0


def test_outdoor_deterministic():
    from datetime import datetime, timezone

    from app import demo_data

    ts = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
    assert demo_data.outdoor_hour(ts) == demo_data.outdoor_hour(ts)
