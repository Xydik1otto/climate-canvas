"""Weekly report: /api/report/weekly stats + /report page."""
import pytest


def test_weekly_report_covers_all_rooms(client):
    from app import config

    r = client.get("/api/report/weekly")
    assert r.status_code == 200
    data = r.json()
    assert data["days"] == 7
    assert set(data["rooms"]) == set(config.DEFAULT_ROOMS)


def test_weekly_report_stats_sane(client):
    data = client.get("/api/report/weekly").json()
    for room, rep in data["rooms"].items():
        assert rep["min"] <= rep["avg"] <= rep["max"]
        assert -30.0 <= rep["min"] <= 45.0
        assert rep["samples"] > 0
        # 7 full days of hourly demo data (plus the current hour bucket)
        assert 7 * 24 <= rep["samples"] <= 7 * 24 + 1
        assert 0.0 <= rep["humidity_avg"] <= 100.0


def test_weekly_report_daily_series(client):
    data = client.get("/api/report/weekly").json()
    for rep in data["rooms"].values():
        assert 7 <= len(rep["daily"]) <= 8
        for d, v in rep["daily"]:
            assert len(d) == 10 and d[4] == "-"  # ISO date
            assert -30.0 <= v <= 45.0
        days = [d for d, _ in rep["daily"]]
        assert days == sorted(days)


def test_report_page_served(client):
    r = client.get("/report")
    assert r.status_code == 200
    assert "Тижневий звіт" in r.text
