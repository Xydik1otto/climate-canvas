"""Tests for data safety: one-click full export (JSON/CSV) + confirmed wipe."""
import csv
import io
import json


def test_export_all_json_contains_everything(client):
    r = client.get("/api/export/all", params={"format": "json"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["app"] == "climate-canvas"
    assert data["exported_at"].startswith("20")
    readings = data["readings"]
    assert len(readings) > 1000  # demo history: 4 rooms × 90 days × 24h × 5 metrics
    rooms = {x["room"] for x in readings}
    assert rooms == {"Living Room", "Bedroom", "Kitchen", "Office"}
    metrics = {x["metric"] for x in readings}
    assert metrics == {"temperature", "humidity", "energy", "co2", "voc"}
    assert all(isinstance(x["value"], (int, float)) for x in readings[:50])


def test_export_all_csv(client):
    r = client.get("/api/export/all", params={"format": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["room", "metric", "ts", "value"]
    assert len(rows) > 1000
    assert {row[0] for row in rows[1:]} == {"Living Room", "Bedroom", "Kitchen", "Office"}


def test_export_all_json_and_csv_have_same_count(client):
    n_json = len(client.get("/api/export/all", params={"format": "json"}).json()["readings"])
    n_csv = len(list(csv.reader(io.StringIO(client.get("/api/export/all", params={"format": "csv"}).text)))) - 1
    assert n_json == n_csv


def test_export_all_bad_format_422(client):
    r = client.get("/api/export/all", params={"format": "xml"})
    assert r.status_code == 422


def test_wipe_requires_explicit_confirm(client):
    r = client.delete("/api/data")
    assert r.status_code == 422
    assert "confirm=DELETE" in r.json()["detail"]
    r = client.delete("/api/data", params={"confirm": "yes"})
    assert r.status_code == 422


def test_wipe_deletes_everything(client):
    client.post("/api/annotations", json={"room": "Bedroom", "ts": "2026-11-01T10:00:00+00:00", "label": "вікно"})
    r = client.delete("/api/data", params={"confirm": "DELETE"})
    assert r.status_code == 200
    assert r.json()["deleted_readings"] > 1000
    # history gone
    tl = client.get("/api/timeline", params={"room": "Bedroom", "metric": "temperature", "days": 7}).json()
    assert tl["points"] == []
    ann = client.get("/api/annotations", params={"room": "Bedroom"}).json()
    assert ann["annotations"] == []
    # health reflects the empty cache
    assert client.get("/api/health").json()["has_data"] is False


def test_wipe_then_reseed_works(client):
    client.delete("/api/data", params={"confirm": "DELETE"})
    r = client.post("/api/demo/seed")
    assert r.status_code == 200
    assert r.json()["points"] > 0
