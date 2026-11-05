"""Configuration for climate-canvas."""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cache.db"
ROOMS_CONFIG = BASE_DIR / "rooms.json"

# Demo mode: on when DEMO=1 or when no HASS token is configured.
_ENV_DEMO = os.environ.get("DEMO", "") == "1"
_ENV_HASS_TOKEN = os.environ.get("HASS_TOKEN", "")
_ENV_HASS_URL = os.environ.get("HASS_URL", "http://supervisor/core/api")

HASS_TOKEN = _ENV_HASS_TOKEN
HASS_URL = _ENV_HASS_URL.rstrip("/")

# User-configured settings (setup wizard in the UI) live in data/settings.json
# and take priority over environment variables.
SETTINGS_FILE = DATA_DIR / "settings.json"


def load_settings(path: Path | None = None) -> dict:
    """Load user settings saved by the setup wizard ({} when absent/corrupt)."""
    p = path or SETTINGS_FILE
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_settings(settings: dict, path: Path | None = None) -> Path:
    """Merge and persist user settings (setup wizard writes URL/token here)."""
    p = path or SETTINGS_FILE
    merged = {**load_settings(p), **settings}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def normalize_hass_url(url: str) -> str:
    """Normalize a user-provided HA base URL to point at the REST API root."""
    u = (url or "").strip().rstrip("/")
    if u and not u.endswith("/api"):
        u += "/api"
    return u


def hass_url(path: Path | None = None) -> str:
    """Configured HA URL: setup wizard (settings.json) first, then env."""
    return (load_settings(path).get("hass_url") or _ENV_HASS_URL).rstrip("/")


def hass_token(path: Path | None = None) -> str:
    """Configured HA token: setup wizard (settings.json) first, then env."""
    return load_settings(path).get("hass_token") or _ENV_HASS_TOKEN


def demo_mode(path: Path | None = None) -> bool:
    """Demo is on when DEMO=1 is set explicitly or no HA token is configured."""
    if _ENV_DEMO:
        return True
    return not hass_token(path)


# Runtime flags (updated by reload() — URL/token take effect for the running
# process, but a demo<->HA switch itself needs a restart, so the data source
# never changes mid-flight).
DEMO = _ENV_DEMO or not hass_token()


def reload() -> None:
    """Re-read URL/token from settings.json (call after the wizard saves).

    Deliberately does NOT flip DEMO: switching between demo data and a real
    Home Assistant instance requires a restart (see POST /api/setup, which
    reports `restart_required`).
    """
    global HASS_URL, HASS_TOKEN
    HASS_URL = hass_url()
    HASS_TOKEN = hass_token()

COMFORT_MIN = 20.0
COMFORT_MAX = 24.0

# Default per-room humidity comfort zone (30–50 % — mold-safe indoor range).
# Overridable per room via humidity_min/humidity_max in rooms.json.
HUMIDITY_MIN = 30.0
HUMIDITY_MAX = 50.0

# Electricity price per kWh for the energy view cost estimate (currency-agnostic).
ENERGY_PRICE = float(os.environ.get("ENERGY_PRICE", "7.5"))

# Open-Meteo (free, no API key) location for outdoor temperature comparison / forecast.
LATITUDE = float(os.environ.get("LATITUDE", "50.4501"))
LONGITUDE = float(os.environ.get("LONGITUDE", "30.5234"))

DEFAULT_ROOMS = {
    "Living Room": {"temp_entity": "sensor.living_room_temp", "humidity_entity": "sensor.living_room_hum", "energy_entity": "sensor.living_room_energy", "co2_entity": "sensor.living_room_co2", "voc_entity": "sensor.living_room_voc"},
    "Bedroom": {"temp_entity": "sensor.bedroom_temp", "humidity_entity": "sensor.bedroom_hum", "energy_entity": "sensor.bedroom_energy", "co2_entity": "sensor.bedroom_co2", "voc_entity": "sensor.bedroom_voc"},
    "Kitchen": {"temp_entity": "sensor.kitchen_temp", "humidity_entity": "sensor.kitchen_hum", "energy_entity": "sensor.kitchen_energy", "co2_entity": "sensor.kitchen_co2", "voc_entity": "sensor.kitchen_voc"},
    "Office": {"temp_entity": "sensor.office_temp", "humidity_entity": "sensor.office_hum", "energy_entity": "sensor.office_energy", "co2_entity": "sensor.office_co2", "voc_entity": "sensor.office_voc"},
}


def load_rooms(path: Path | None = None) -> dict:
    """Load rooms config; fall back to defaults when the file is absent."""
    p = path or ROOMS_CONFIG
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return DEFAULT_ROOMS


def save_rooms(rooms: dict, path: Path | None = None) -> Path:
    """Persist a rooms mapping to rooms.json (used by the discovery UI)."""
    p = path or ROOMS_CONFIG
    p.write_text(json.dumps(rooms, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p
