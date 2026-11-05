# climate-canvas

![tests](https://github.com/bigpi/climate-canvas/actions/workflows/tests.yml/badge.svg)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![version](https://img.shields.io/badge/version-0.4.0-blue)

**Home Climate & Energy Canvas** — довгострокова візуалізація клімату та енергії з Home Assistant.

## Чому це існує

Цей дашборд з'явився через реальний, підтверджений біль користувачів Home Assistant —
дані є, а довгострокової картини немає:

> «The current statistics graph in Home Assistant is suboptimal. … Better graphical
> representations of temperature/humidity changes over time are needed.»
> — обговорення у community.home-assistant.io (feature requests)

Додаткові свідчення з тих самих обговорень:

- користувачі скаржаться, що стандартні графіки «show only 24h» і не дають
  порівняти сезон з сезоном чи знайти, *коли саме* вдома стало волого;
- про конденсацію і цвіль дізнаються постфактум — коли на вікні вже швидне,
  хоча сенсори мали попередити за тиждень до того.

climate-canvas закриває саме цей розрив: локальний, легкий (FastAPI + Chart.js,
без хмари і без Docker) дашборд, який зберігає історію скільки завгодно довго
і показує її так, як це зручно людині — картки кімнат, таймлайни, теплові мапи
«день × година» і тепер ще точка роси, порівняння з вулицею, прогноз і тижневий звіт.

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

### Енергія (v0.2)

- **View «Енергія»** — kWh-сенсори (`unit_of_measurement: kWh`) в окремій вкладці:
  стовпчикова діаграма kWh/день, сумарне споживання і **вартість**.
- Ціна kWh налаштовується: поле вводу в UI (зберігається в localStorage) або
  змінна середовища `ENERGY_PRICE` (за замовчуванням 7.5). API: `GET /api/energy?room=&days=&price=`.
- У `rooms.json` додайте ключ `"energy_entity": "sensor.xxx_energy"` для кімнат
  з лічильником (Shelly/ESPHome/Deye тощо).

### Мітки на таймлайні (v0.2)

- **Alerts/annotations** — клік по графіку таймлайна створює мітку («відкрито вікно»,
  «відпустка», «новий термостат»); зберігається в SQLite (`annotations`), малюється
  вертикальною пунктирною лінією з підписом на графіку.
- Список міток під графіком з кнопкою видалення.
- API: `GET/POST /api/annotations`, `DELETE /api/annotations/{id}`.

### CO₂ / VOC (v0.2)

- Сенсори якості повітря підтримуються скрізь, де є сенсор: одиниці `ppm` → CO₂,
  `ppb` → VOC. Ключі в `rooms.json`: `"co2_entity"`, `"voc_entity"` (опціональні).
- Таймлайн має опції CO₂/VOC (перевірка якості повітря: >1000 ppm — провітрити),
  картки кімнат показують 🫁 ppm та 🧪 ppb, якщо сенсор є.
- Demo-генератор моделює добову динаміку CO₂ (люди вдома ввечері — до ~800 ppm).

### Темна/світла тема (v0.2)

- Кнопка ☀️/🌙 у шапці перемикає тему; вибір зберігається у `localStorage`.
- Кольори — CSS-змінні; графіки Chart.js читають їх під час рендеру й одразу
  перефарбовуються після переключення.

### Точка роси та ризик цвілі (v0.4)

- Психрометрична **формула Магнуса** (`app/climate.py`): точка роси з T + RH.
- На картках кімнат: 🌡 точка роси + індикатор ризику цвілі
  (високий = RH ≥ 70 % при T < 20 °C, середній = RH ≥ 65 %).
- У тепловій мапі нові метрики: **Точка роси** та **Ризик цвілі**
  (зелений/жовтий/червоний) — видно, в які години і дні ризик конденсації.
- API: `dew_point`/`mold_risk` у `/api/rooms`, `metric=dew_point|mold_risk` у `/api/heatmap`.

### Зовнішня температура (v0.4)

- **Open-Meteo** (безкоштовно, без ключа): фактична температура зовні за
  архівним API за останні N днів — пунктирний оверлей «Зовні» на таймлайні.
- Координати — у конфігу: змінні середовища `LATITUDE` / `LONGITUDE`
  (за замовчуванням Київ). Відповідь кешується на годину.
- API: `GET /api/outdoor?days=N` → `{points, source, location}`.

### Прогноз на 48 год (v0.4)

- Чекбокс «Прогноз 48 год» на таймлайні температури: синя пунктирна крива
  майбутнього продовжує історію (Open-Meteo Forecast API).
- API: `GET /api/forecast?hours=48`.
- У demo-режимі обидва джерела (архів і прогноз) — детермінований синтетичний
  «зовнішній» генератор, тож працює без інтернету.

### Тижневий звіт (v0.4)

- Сторінка **/report** (іконка 📊 у шапці): SVG-графік денних середніх по всіх
  кімнатах + таблиця середнє/мін/макс температури, середня вологість, кількість точок.
- API: `GET /api/report/weekly`.

### PWA (v0.4)

- `static/manifest.webmanifest` + SVG-іконка: дашборд можна «встановити»
  на телефон/десктоп як окремий застосунок.


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

## Статус (roadmap)

| Функція | Стан |
|---|---|
| 4 базові вьюхи, demo + HA, кеш, тести (MVP) | ✅ |
| Lifespan, CSV export, авто-виявлення сенсорів, вологість-мапа (v0.1.0-alpha) | ✅ |
| Енергія kWh + вартість, мітки на таймлайні, CO₂/VOC, тема (v0.3.0) | ✅ |
| Точка роси + ризик цвілі, зовнішня температура (Open-Meteo), прогноз 48 год, тижневий звіт, PWA manifest (v0.4.0) | ✅ |
| «тиждень vs минулий тиждень», push-нотифікації про ризик цвілі | ⏳ |

## Smoke-тест

```bash
bash scripts/smoke.sh   # піднімає демо-сервер на випадковому порті, перевіряє ендпоінти, PASS/FAIL
```

## Ліцензія

MIT — див. [LICENSE](LICENSE). Проєкт локальний, дані не залишають вашої машини.
