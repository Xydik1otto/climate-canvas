# PLAN — climate-canvas (Home Climate & Energy Canvas)

## 1. Аудиторія

- Власники Home Assistant з температурними/вологісними сенсорами по кімнатах.
- Люди з термостатами, тепловими насосами, енергомоніторингом (Shelly, ESPHome).
- «Data-nerds», які хочуть дивитися на довгі часові ряди (тижні/місяці/сезони),
  а не тільки на поточне значення сенсора.

Біль: стандартні графіки HA зручні для «за останню добу», але погані для
довгих горизонтів і порівнянь; легенди перевантажені; теплових мап немає.

## 2. MVP scope (цей реліз)

| Функція | Стан |
|---|---|
| Room card grid: поточні темп/вологість + комфорт-зони | ✅ |
| Timeline 7/30/90 днів з day/night shading (Chart.js) | ✅ |
| Теплова мапа «дні × години» по кімнатах (SVG) | ✅ |
| Порівняння сезонів (місяць X року A vs року B) | ✅ |
| Home Assistant REST джерело (`/api/states`, `/api/history/period`) | ✅ |
| Demo mode з детермінованими синтетичними даними | ✅ |
| Локальний кеш SQLite + авто-pull щогодини | ✅ |
| Конфіг кімнат (`rooms.json`) | ✅ |

Поза MVP: авторизація/користувачі, мобільний додаток, прогнози, енергоспоживання
у kWh (частково в v1.1), push-сповіщення.

## 3. Архітектура

```
browser (vanilla JS + Chart.js CDN)
   │  fetch /api/*
   ▼
FastAPI (app/main.py)
   ├── ha_client.py   → Home Assistant REST API (httpx, Bearer HASS_TOKEN)
   ├── demo_data.py   → детермінований синтетичний генератор (seed = дата+кімната)
   ├── cache.py       → SQLite: readings(room, metric, ts, value)
   └── aggregate.py   → hourly mean, heatmap-матриця, сезонні середні
   ▼
static/ (index.html, app.js, style.css)
```

Потік даних: щогодини фоновий потік тягне `/api/history/period` за останній день
по всіх entity з `rooms.json`, парсить у readings, складає в SQLite. UI читає
тільки з кешу + `/api/states` (через кеш-проксі) для «поточних» значень.

### Конфіг кімнат (`rooms.json`)

```json
{
  "Вітальня": {"temp_entity": "sensor.living_room_temp", "humidity_entity": "sensor.living_room_hum"},
  "Спальня":  {"temp_entity": "sensor.bedroom_temp", "humidity_entity": "sensor.bedroom_hum"}
}
```

## 4. API

- `GET /api/rooms` — поточні значення по кімнатах (+ комфорт-зона).
- `GET /api/timeline?room=&metric=&days=7|30|90` — щогодинні точки.
- `GET /api/heatmap?room=&days=90` — матриця days×hours середньої температури.
- `GET /api/seasons?room=&month=1` — середні за місяць для кількох років.
- `GET /` — статичний дашборд.

## 5. Roadmap

- **v0.1 (MVP, поточний)** — 4 вьюхи, demo + HA, кеш, тести.
- **v1.0** — енергія (kWh-сенсори), export CSV, авто-виявлення сенсорів з HA.
- **v1.1** — компаньйон-представлення: «тиждень vs минулий тиждень», anomaly notes.
- **v1.2** — пакетний «Pro pack» (one-time): додаткові вьюхи (вологість-мапа,
  CO₂), автоматичні звіти тижня.

## 6. Монетизація

- **GitHub Sponsors** — базовий фінансування open-source розвитку.
- **Pro Pack (one-time, ~$10)**: додаткові вьюхи (вологість, CO₂, енергія),
  звіти PDF/PNG, пріоритетні фічі. Ядро назавжди безкоштовне й локальне
  (відповідь на subscription fatigue — жодних підписок).

## 7. Ризики

| Ризик | Мітигація |
|---|---|
| HA API змінює формат history | Парсер ізольований в `ha_client.py`, тести на зафіксованих фікстурах |
| Великий обсяг даних (роки) | Агрегація в SQLite на рівні годин; сировина чиститься після агрегації |
| Користувач без HA не бачить цінності | Demo mode з реалістичними даними з першого запуску |
| Cloud-туunnel спокуси | Жодних зовнішніх викликів крім локального HA; privacy як фіча |
| Робота на слабких залізничних хостах (Raspberry) | Чистий Python + SQLite, без тяжких залежностей |

## 8. Критерії готовності MVP

- `pytest` проходить (парсинг HA-фікстур, агрегація, детермінізм демо, API).
- `uvicorn app.main:app` піднімається без HA (demo mode) і дашборд малює всі 4 вьюхи.
- З реальним HA: card grid показує живі значення; кеш росте після hourly pull.
