"""Shared pytest fixtures: recorded HA API responses + temp dirs."""
import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Demo volume for the `client` fixture. Every API test uses <= 30 days of
# history, so 32 days keeps full coverage while cutting fixture setup ~3x.
# Override with CLIMATE_CANVAS_TEST_DAYS (e.g. 90 to reproduce full volume).
TEST_DEMO_DAYS = int(os.environ.get("CLIMATE_CANVAS_TEST_DAYS", "32"))


def load_fixture(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def states_fixture():
    return load_fixture("states")


@pytest.fixture
def history_fixture():
    return load_fixture("history_period")


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient in demo mode with an isolated temp database."""
    from fastapi.testclient import TestClient

    from app import config, demo_data, main

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr(config, "DEMO", True)
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    main._cache = None
    with TestClient(main.app) as c:
        demo_data.seed_cache(main.get_cache(), days=TEST_DEMO_DAYS)
        yield c
    main._cache = None
