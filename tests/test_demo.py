"""Tests for the deterministic demo generator."""
from datetime import datetime, timezone

from app.demo_data import generate_hours, hour_value, seed_cache


def test_deterministic_same_inputs_same_output():
    ts = datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)
    a = hour_value("Bedroom", ts, "temperature")
    b = hour_value("Bedroom", ts, "temperature")
    assert a == b


def test_deterministic_full_series():
    end = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
    s1 = generate_hours("Kitchen", hours=48, end=end)
    s2 = generate_hours("Kitchen", hours=48, end=end)
    assert s1 == s2


def test_plausible_ranges():
    ts = datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)
    t = hour_value("Bedroom", ts, "temperature")
    h = hour_value("Bedroom", ts, "humidity")
    assert -20.0 <= t <= 45.0
    assert 10.0 <= h <= 100.0


def test_day_warmer_than_night_on_average():
    end = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    series = generate_hours("Living Room", hours=24 * 30, end=end)
    day_vals, night_vals = [], []
    for rd in series:
        if rd["metric"] != "temperature":
            continue
        hour = int(rd["ts"][11:13])
        (day_vals if 10 <= hour < 20 else night_vals).append(rd["value"])
    assert sum(day_vals) / len(day_vals) > sum(night_vals) / len(night_vals)


def test_seed_cache_populates_db(tmp_path):
    from app.cache import Cache

    db = Cache(tmp_path / "test.db")
    rooms = {"TestRoom": {"temp_entity": "sensor.test_temp", "humidity_entity": "sensor.test_hum"}}
    seed_cache(db, rooms=rooms, days=3)
    assert db.count() == 3 * 24 * 2  # temp + humidity per hour
