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
