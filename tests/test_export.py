"""Tests for the CSV export endpoint."""
import csv
import io


def test_csv_export_headers_and_content(client):
    r = client.get("/api/export/csv", params={"room": "Bedroom", "metric": "temperature", "days": 2})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert "bedroom_temperature_2d.csv" in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["ts", "temperature"]
    # 2 days of hourly demo data + header
    assert len(rows) == 1 + 2 * 24
    ts, value = rows[1]
    assert ts.startswith("20")
    assert float(value)  # numeric, non-zero


def test_csv_export_humidity(client):
    r = client.get("/api/export/csv", params={"room": "Kitchen", "metric": "humidity", "days": 1})
    assert r.status_code == 200
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["ts", "humidity"]
    assert len(rows) == 25


def test_csv_export_unknown_room_404(client):
    r = client.get("/api/export/csv", params={"room": "Atlantis", "metric": "temperature"})
    assert r.status_code == 404


def test_csv_export_bad_metric_422(client):
    r = client.get("/api/export/csv", params={"room": "Kitchen", "metric": "banana"})
    assert r.status_code == 422
