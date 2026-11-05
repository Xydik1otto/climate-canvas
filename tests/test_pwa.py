"""PWA manifest + icon are served and linked."""
import json


def test_manifest_served_and_valid(client):
    r = client.get("/static/manifest.webmanifest")
    assert r.status_code == 200
    m = json.loads(r.text)
    assert m["name"] == "Climate Canvas"
    assert m["start_url"] == "/"
    assert m["display"] == "standalone"
    assert m["icons"] and m["icons"][0]["src"] == "/static/icon.svg"


def test_icon_served(client):
    r = client.get("/static/icon.svg")
    assert r.status_code == 200
    assert "<svg" in r.text


def test_index_links_manifest(client):
    html = client.get("/").text
    assert 'rel="manifest"' in html and "/static/manifest.webmanifest" in html
    assert 'rel="icon"' in html
