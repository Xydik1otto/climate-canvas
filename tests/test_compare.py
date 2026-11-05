"""Порівняння кімнат: /api/compare — денні серії temp/humidity для графіка."""
from app import config


def test_compare_temperature_covers_all_rooms(client):
    r = client.get("/api/compare", params={"metric": "temperature", "days": 7})
    assert r.status_code == 200
    data = r.json()
    assert data["metric"] == "temperature" and data["days"] == 7
    assert set(data["rooms"]) == set(config.DEFAULT_ROOMS)  # у демо всі кімнати мають сенсори


def test_compare_humidity_and_stats_sane(client):
    data = client.get("/api/compare", params={"metric": "humidity", "days": 7}).json()
    assert data["metric"] == "humidity"
    for room, rep in data["rooms"].items():
        assert rep["min"] <= rep["avg"] <= rep["max"]
        assert 0.0 <= rep["avg"] <= 100.0
        assert rep["samples"] > 0


def test_compare_daily_series_sorted_iso(client):
    data = client.get("/api/compare", params={"days": 7}).json()
    for rep in data["rooms"].values():
        assert 7 <= len(rep["daily"]) <= 8  # 7 повних днів + поточний бакет
        days = [d for d, _ in rep["daily"]]
        assert days == sorted(days)
        assert all(len(d) == 10 and d[4] == "-" for d in days)


def test_compare_rejects_unknown_metric(client):
    r = client.get("/api/compare", params={"metric": "co2"})
    assert r.status_code == 422


def test_compare_skips_rooms_without_sensor(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOMS_CONFIG", tmp_path / "rooms.json")
    rooms = {
        "Kitchen": {"temp_entity": "s.k", "humidity_entity": "s.kh"},
        "Garage": {"humidity_entity": "s.g"},  # немає температурного сенсора
    }
    config.save_rooms(rooms)  # конфіг пишемо напрямом: /rooms/config вимагає обидва сенсори
    data = client.get("/api/compare", params={"metric": "temperature"}).json()
    assert set(data["rooms"]) == {"Kitchen"}  # Garage відфільтрований


def test_compare_matches_timeline_values(client):
    """Денне середнє з /api/compare збігається з денним середнім timeline-точок."""
    data = client.get("/api/compare", params={"metric": "temperature", "days": 7}).json()
    rep = data["rooms"]["Bedroom"]
    tl = client.get("/api/timeline", params={
        "room": "Bedroom", "metric": "temperature", "days": 7}).json()
    by_day: dict[str, list[float]] = {}
    for ts, v in tl["points"]:
        by_day.setdefault(ts[:10], []).append(v)
    expected = {d: round(sum(v) / len(v), 2) for d, v in by_day.items()}
    got = dict(rep["daily"])
    assert got == expected
