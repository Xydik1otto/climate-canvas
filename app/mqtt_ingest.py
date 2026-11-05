"""MQTT-інжесція сенсорів Zigbee2MQTT у локальний кеш.

Z2M публікує стан кожного пристрою як JSON у топік
`zigbee2mqtt/<Friendly Name>` (плюс вложені топіки `.../action` тощо).
Ми мапимо friendly name → кімнату з settings.json (`mqtt_rooms`) і
складаємо впізнані метрики (temperature/humidity/co2/voc) у readings.

paho-mqtt НЕ входить у базові залежності: клієнт підключається ліниво,
а `handle()` (парсинг + запис у кеш) повністю тестований без мережі.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import cache as cache_mod

DEFAULT_PREFIX = "zigbee2mqtt/"

# ключі в payload Z2M → метрика в нашому кеші
PAYLOAD_METRICS = {
    "temperature": "temperature",
    "humidity": "humidity",
    "co2": "co2",
    "carbon_dioxide": "co2",
    "voc": "voc",
}


def parse_message(
    topic: str,
    payload: bytes | str,
    mapping: dict[str, str],
    prefix: str = DEFAULT_PREFIX,
    now: datetime | None = None,
) -> list[tuple[str, str, str, float]]:
    """Один Z2M-публікація → [(room, metric, ts, value)]; [] — якщо не наш топік.

    Топік має починатися з `prefix`, перший сегмент після нього — friendly
    name, який шукаємо в `mapping` (точно або без урахування регістру).
    """ 
    if prefix and not topic.startswith(prefix):
        return []
    friendly = topic[len(prefix):].split("/", 1)[0].strip()
    lookup = {k.lower(): v for k, v in mapping.items()}
    room = lookup.get(friendly) or lookup.get(friendly.lower())
    if not room or not isinstance(payload, (bytes, str)):
        return []
    try:
        data = json.loads(payload)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []

    ts = _reading_ts(data.get("last_seen"), now)
    values: dict[str, float] = {}
    for key, metric in PAYLOAD_METRICS.items():  # синоніми не перекривають канонічні
        value = data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.setdefault(metric, float(value))
    return [(room, metric, ts, v) for metric, v in values.items()]


def _reading_ts(last_seen, now: datetime | None = None) -> str:
    """Годинний бакет ISO: з payload.last_seen (якщо парситься) або « зараз»."""
    if isinstance(last_seen, str):
        try:
            dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.replace(minute=0, second=0, microsecond=0).strftime(
                "%Y-%m-%dT%H:00:00+00:00"
            )
        except ValueError:
            pass
    now = now or datetime.now(timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00:00+00:00")


class MqttIngestor:
    """Обробка вхідних повідомлень + (опційно) реальний paho-клієнт."""

    def __init__(self, db: cache_mod.Cache, mapping: dict[str, str], prefix: str = DEFAULT_PREFIX):
        self.db = db
        self.mapping = {str(k): str(v) for k, v in (mapping or {}).items()}
        self.prefix = prefix

    def handle(self, topic: str, payload: bytes | str) -> int:
        """Записати впізнані значення в кеш; повертає кількість рядків."""
        rows = parse_message(topic, payload, self.mapping, self.prefix)
        if rows:
            self.db.add_readings(rows)
        return len(rows)

    def start(self, host: str, port: int = 1883, keepalive: int = 60):
        """Підключитися до брокера і слухати `prefix#`. Потрібен paho-mqtt."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:  # необов'язкова залежність
            raise RuntimeError(
                "MQTT ingestion needs paho-mqtt: pip install paho-mqtt"
            ) from exc

        client = mqtt.Client(client_id="climate-canvas")
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.connect(host, int(port), keepalive)
        client.loop_start()
        return client

    def _on_connect(self, client, _userdata, _flags, rc):
        client.subscribe(self.prefix + "#")

    def _on_message(self, _client, _userdata, msg):
        self.handle(msg.topic, msg.payload)
