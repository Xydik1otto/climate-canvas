"""Packaging checks: pyproject metadata, entry point, app version."""
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_metadata():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "climate-canvas"
    assert project["version"] == "1.0.0"
    assert sys.version_info >= (3, 11)
    deps = " ".join(project["dependencies"])
    for pkg in ("fastapi", "uvicorn", "httpx", "reportlab"):
        assert pkg in deps
    assert project["scripts"]["climate-canvas"] == "app.main:cli"


def test_console_entry_point_exists():
    from app import main

    assert callable(main.cli)


def test_app_version_is_1_0_0():
    from app import main

    assert main.app.version == "1.0.0"


def test_pinned_requirements_match_pyproject():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for pkg in ("fastapi", "uvicorn", "httpx", "reportlab"):
        assert pkg in req


def test_package_importable():
    import importlib

    for mod in ("app.main", "app.config", "app.cache", "app.report_pdf", "app.ha_client",
                "app.demo_data", "app.discover", "app.openmeteo", "app.sync", "app.climate"):
        importlib.import_module(mod)
