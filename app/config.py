"""Configuration for climate-canvas."""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cache.db"
ROOMS_CONFIG = BASE_DIR / "rooms.json"

# Demo mode: on when DEMO=1 or when no HASS token is configured.
DEMO = os.environ.get("DEMO", "") == "1" or not os.environ.get("HASS_TOKEN")

HASS_TOKEN = os.environ.get("HASS_TOKEN", "")
HASS_URL = os.environ.get("HASS_URL", "http://supervisor/core/api").rstrip("/")

COMFORT_MIN = 20.0
COMFORT_MAX = 24.0

# Electricity price per kWh for the energy view cost estimate (currency-agnostic).
ENERGY_PRICE = float(os.environ.get("ENERGY_PRICE", "7.5"))

DEFAULT_ROOMS = {
    "Living Room": {"temp_entity": "sensor.living_room_temp", "humidity_entity": "sensor.living_room_hum", "energy_entity": "sensor.living_room_energy"},
    "Bedroom": {"temp_entity": "sensor.bedroom_temp", "humidity_entity": "sensor.bedroom_hum", "energy_entity": "sensor.bedroom_energy"},
    "Kitchen": {"temp_entity": "sensor.kitchen_temp", "humidity_entity": "sensor.kitchen_hum", "energy_entity": "sensor.kitchen_energy"},
    "Office": {"temp_entity": "sensor.office_temp", "humidity_entity": "sensor.office_hum", "energy_entity": "sensor.office_energy"},
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
