"""Tests for the dark/light theme toggle."""


def test_index_has_theme_toggle(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'id="theme-toggle"' in r.text


def test_stylesheet_defines_light_theme(client):
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert "body.light" in r.text
    assert "--accent" in r.text  # theme colors are CSS variables
