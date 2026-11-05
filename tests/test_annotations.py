"""Tests for user annotations on the timeline (SQLite-backed)."""


def test_create_and_list_annotation(client):
    ts = "2026-01-10T10:00:00+00:00"
    r = client.post("/api/annotations", json={"room": "Bedroom", "ts": ts, "label": "відкрито вікно"})
    assert r.status_code == 200
    ann = r.json()
    assert ann["id"] > 0
    assert ann["label"] == "відкрито вікно"

    r = client.get("/api/annotations", params={"room": "Bedroom", "days": 365})
    items = r.json()["annotations"]
    assert any(i["id"] == ann["id"] and i["label"] == "відкрито вікно" for i in items)


def test_annotation_scoped_to_room(client):
    r = client.post("/api/annotations", json={"room": "Kitchen", "ts": "2026-01-10T10:00:00+00:00", "label": "кухня"})
    kid = r.json()["id"]
    r = client.get("/api/annotations", params={"room": "Bedroom", "days": 365})
    assert all(i["id"] != kid for i in r.json()["annotations"])


def test_annotation_unknown_room_404(client):
    r = client.post("/api/annotations", json={"room": "Atlantis", "ts": "2026-01-10T10:00:00+00:00", "label": "x"})
    assert r.status_code == 404
    r = client.get("/api/annotations", params={"room": "Atlantis"})
    assert r.status_code == 404


def test_annotation_validation_errors(client):
    # empty label
    r = client.post("/api/annotations", json={"room": "Kitchen", "ts": "2026-01-10T10:00:00+00:00", "label": "  "})
    assert r.status_code == 422
    # bad timestamp
    r = client.post("/api/annotations", json={"room": "Kitchen", "ts": "not-a-date", "label": "x"})
    assert r.status_code == 422


def test_delete_annotation(client):
    r = client.post("/api/annotations", json={"room": "Office", "ts": "2026-01-10T10:00:00+00:00", "label": "відпустка"})
    ann_id = r.json()["id"]
    assert client.delete(f"/api/annotations/{ann_id}").json()["deleted"] == ann_id
    # second delete → 404
    assert client.delete(f"/api/annotations/{ann_id}").status_code == 404


def test_annotations_persist_in_cache(client):
    """Annotations live in SQLite, not in the readings table."""
    from app import main

    cache = main.get_cache()
    ann_id = cache.add_annotation("Kitchen", "2026-01-10T08:00:00+00:00", "test")
    assert cache.annotations_since("Kitchen", "1970-01-01T00:00:00+00:00") == [
        (ann_id, "2026-01-10T08:00:00+00:00", "test")
    ]
    assert cache.count() > 0  # readings untouched
