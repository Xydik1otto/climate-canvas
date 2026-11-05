"""Dew point (Magnus formula) + mold risk: pure math and API surface."""
import pytest

from app import climate


def test_dew_point_reference_values():
    # Well-known psychrometric references (Magnus formula).
    assert climate.dew_point(20.0, 50.0) == pytest.approx(9.27, abs=0.15)
    assert climate.dew_point(25.0, 75.0) == pytest.approx(20.28, abs=0.15)
    assert climate.dew_point(0.0, 100.0) == pytest.approx(0.0, abs=0.05)


def test_dew_point_never_above_air_temp():
    for t in (5.0, 18.4, 22.0, 30.0):
        for rh in (30.0, 60.0, 90.0):
            assert climate.dew_point(t, rh) <= t + 1e-9


def test_dew_point_rejects_invalid_rh():
    with pytest.raises(ValueError):
        climate.dew_point(20.0, 0.0)
    with pytest.raises(ValueError):
        climate.dew_point(20.0, 150.0)


def test_mold_risk_thresholds():
    assert climate.mold_risk(18.0, 75.0) == "high"   # RH>=70% at T<20°C
    assert climate.mold_risk(15.0, 70.0) == "high"
    assert climate.mold_risk(22.0, 75.0) == "medium"  # warm but very humid
    assert climate.mold_risk(18.0, 66.0) == "medium"
    assert climate.mold_risk(21.0, 45.0) == "low"
    assert climate.mold_risk(20.0, 70.0) == "medium"  # boundary: T=20 is not <20


def test_risk_level_mapping():
    assert climate.RISK_LEVEL == {"low": 0, "medium": 1, "high": 2}


def test_rooms_include_dew_point_and_risk(client):
    r = client.get("/api/rooms")
    assert r.status_code == 200
    for st in r.json()["rooms"].values():
        assert st["dew_point"] is not None
        assert st["mold_risk"] in ("low", "medium", "high")
        assert st["dew_point"] <= st["temperature"] + 1e-9


def test_heatmap_dew_point(client):
    r = client.get("/api/heatmap", params={"room": "Bedroom", "metric": "dew_point", "days": 30})
    assert r.status_code == 200
    m = r.json()
    assert len(m["values"]) == 30
    flat = [v for row in m["values"] for v in row if v is not None]
    assert flat and all(-40.0 <= v <= 40.0 for v in flat)


def test_heatmap_mold_risk(client):
    r = client.get("/api/heatmap", params={"room": "Kitchen", "metric": "mold_risk", "days": 30})
    assert r.status_code == 200
    m = r.json()
    flat = [v for row in m["values"] for v in row if v is not None]
    assert flat and all(v in (0, 1, 2) for v in flat)


def test_heatmap_mold_risk_unknown_room_404(client):
    r = client.get("/api/heatmap", params={"room": "Atlantis", "metric": "mold_risk"})
    assert r.status_code == 404
