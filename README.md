# climate-canvas

![tests](https://github.com/bigpi/climate-canvas/actions/workflows/tests.yml/badge.svg)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![version](https://img.shields.io/badge/version-0.1.0--alpha-orange)

**Home Climate & Energy Canvas** — довгострокова візуалізація клімату та енергії з Home Assistant.

## Проблема

Home Assistant чудово збирає дані, але погано їх показує на довгих горизонтах:

- Офіційний блог Home Assistant визнає, що графіки з легендами «suboptimal» (неоптимальні).
- Ком'юніті скаржиться, що статистичні графіки обмежені; власники сенсорів хочуть
  «better graphical representations of temperature/humidity changes over time».
- Теплових мап будинку (день × година по кімнатах) у стандартному UI взагалі немає.

## Рішення (ALPHA v0.1.0)

Легкий локальний веб-дашборд: Python FastAPI бекенд + чистий HTML/JS/Chart.js фронтенд
(CDN, без build-кроку). Дані — з Home Assistant REST API або з демо-генератора.

### Вьюхи

1. **Room card grid** — поточні температура/вологість по кімнатах з комфорт-зонами.
2. **Timeline** — графік на 7/30/90 днів із затіненням день/ніч.
3. **Heatmap** — матриця «дні × години», з перемикачем метрики: температура **і** вологість (SVG).
4. **Seasons** — порівняння сезонів (наприклад, січень 2025 vs січень 2026).

### Що з'явилося в alpha

- **Експорт CSV** — `GET /api/export/csv?room=&metric=&days=` віддає сирі щогодинні
  точки з кешу (Excel/LibreOffice-friendly, `Content-Disposition: attachment`).
- **Авто-виявлення сенсорів** — сторінка `/settings`: бекенд парсить `/api/states` HA,
  групує `sensor.*` температуру/вологість по areas (`area_id` або перше слово
  friendly_name) і пропонує готовий мапінг кімнат; кнопка «Зберегти» пише `rooms.json`
  (API: `GET /api/discover`, `POST /api/rooms/config`).
- **Теплова мапа вологості** — перемикач метрики у вкладці Heatmap, окрема шкала кольорів.
- **FastAPI lifespan** замість застарілого `on_event` — чистий лог без DeprecationWarning.

## Джерела даних

- **Home Assistant REST API**: `/api/states` та `/api/history/period`.
  Токен — у змінній середовища `HASS_TOKEN`; базовий URL — `HASS_URL`
  (за замовчуванням `http://supervisor/core/api`, альтернатива
  `http://homeassistant.local:8123`).
- **Demo mode** — детерміновані синтетичні дані, щоб усе працювало без HA.
  Увімкається через `DEMO=1` або автоматично, якщо `HASS_TOKEN` не задано.

### Налаштування HASS_TOKEN

1. У Home Assistant: Profile → Security → **Long-Lived Access Tokens** → Create Token.
2. Передайте токен змінною середовища:

```bash
export HASS_TOKEN="ваш_довгоживучий_токен"
export HASS_URL="http://homeassistant.local:8123"   # або supervisor URL на HA OS
python -m uvicorn app.main:app
```

Без `HASS_TOKEN` застосунок стартує у demo-режимі — реальний HA не потрібен.

## Швидкий старт

```bash
cd climate-canvas
pip install -r requirements.txt

# демо-режим (без Home Assistant)
python -m uvicorn app.main:app --reload
# або з реальним HA:
export HASS_TOKEN=ваш_довгоживучий_токен
export HASS_URL=http://homeassistant.local:8123
python -m uvicorn app.main:app --reload

# тести
pytest
```

Відкрийте http://127.0.0.1:8000 — дашборд із вкладками Rooms / Timeline / Heatmap / Seasons,
налаштування сенсорів — на http://127.0.0.1:8000/settings.

## Скріншоти

> TODO: додати реальні скріншоти (demo mode робить їх відтворюваними).

![Room cards](docs/screenshots/rooms.png)
![Timeline](docs/screenshots/timeline.png)
![Heatmap](docs/screenshots/heatmap.png)
![Seasons](docs/screenshots/seasons.png)

## Кеш

SQLite (`data/cache.db`) зберігає довгу історію; бекенд підтягує нові дані
з HA раз на годину (у demo-режимі кеш заповнюється генератором).

## Ліцензія

MIT — див. [LICENSE](LICENSE). Проєкт локальний, дані не залишають вашої машини.
