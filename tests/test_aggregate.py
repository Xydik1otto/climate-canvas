"""Tests for aggregation: hourly means, heatmap matrix, seasonal means."""
from app.cache import heatmap_matrix, hourly_mean, seasonal_means


def test_hourly_mean_buckets_subhourly_points():
    points = [
        ("2026-01-10T10:15:00+00:00", 21.0),
        ("2026-01-10T10:45:00+00:00", 23.0),
        ("2026-01-10T11:15:00+00:00", 20.0),
    ]
    out = hourly_mean(points)
    assert out == [("2026-01-10T10:00:00+00:00", 22.0), ("2026-01-10T11:00:00+00:00", 20.0)]


def test_hourly_mean_empty():
    assert hourly_mean([]) == []


def test_heatmap_matrix_shape_and_values():
    points = []
    for day in ("2026-01-01", "2026-01-02"):
        for hour in range(24):
            points.append((f"{day}T{hour:02d}:30:00+00:00", float(hour)))
    matrix = heatmap_matrix(points, days=7)
    assert matrix["days"] == ["2026-01-01", "2026-01-02"]
    assert matrix["hours"] == list(range(24))
    assert len(matrix["values"]) == 2
    assert matrix["values"][0][0] == 0.0
    assert matrix["values"][1][23] == 23.0


def test_heatmap_matrix_none_for_missing_hours():
    points = [("2026-01-01T05:30:00+00:00", 21.0)]
    matrix = heatmap_matrix(points, days=7)
    assert matrix["values"][0][5] == 21.0
    assert matrix["values"][0][6] is None
    assert matrix["values"][0][0] is None


def test_heatmap_respects_days_limit():
    points = [(f"2026-01-{d:02d}T10:00:00+00:00", 20.0) for d in range(1, 11)]
    matrix = heatmap_matrix(points, days=5)
    assert matrix["days"] == ["2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09", "2026-01-10"]


def test_seasonal_means_per_year():
    # Caller pre-filters points to the target month (as /api/seasons does).
    points = [
        ("2025-01-15T12:00:00+00:00", -3.0),
        ("2025-01-20T12:00:00+00:00", -1.0),
        ("2026-01-15T12:00:00+00:00", 1.0),
        ("2026-02-15T12:00:00+00:00", 5.0),  # other month — filtered out below
    ]
    january = [(ts, v) for ts, v in points if int(ts[5:7]) == 1]
    out = seasonal_means(january)
    assert out == {"2025": -2.0, "2026": 1.0}
