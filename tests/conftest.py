"""Shared pytest fixtures: recorded HA API responses + temp dirs."""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


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

    from app import config, main

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr(config, "DEMO", True)
    main._cache = None
    with TestClient(main.app) as c:
        yield c
    main._cache = None
