# Changelog

Усі помітні зміни проєкту документуються тут. Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/),
версіонування — [SemVer](https://semver.org/lang/uk/).

## [1.0.0] — 2026-11-05

### Додано
- **Home Assistant setup wizard** — сторінка `/settings`: URL інстансу + довготривалий
  токен з кнопкою «Перевірити з'єднання»; зберігається у `data/settings.json`
  (env-змінні `HASS_TOKEN`/`HASS_URL` далі працюють, wizard має пріоритет).
  API: `GET/POST /api/setup`, `POST /api/setup/test`.
- **Per-room зони вологості** — `humidity_min`/`humidity_max` у `rooms.json`
  (за замовчуванням 30–50 %), редагування в UI налаштувань; картки кімнат
  підсвічують вологість відносно зони; `/api/rooms` повертає `humidity_comfort`.
- **Тижневий звіт у PDF** (reportlab) — `GET /api/report/weekly.pdf`;
  **опційний email** через SMTP — `POST /api/report/email`, налаштування SMTP
  у UI сторінки звіту (`GET/POST /api/smtp`).
- **UA/EN i18n у всьому UI** — `static/i18n.js` (JSON-словники), авто-детект мови
  браузера, збереження вибору, перемикач на всіх сторінках; без російської.
- **First-run experience** — демо-дані більше не сіються автоматично: банер
  «📦 Завантажити демо» (opt-in, `POST /api/demo/seed`), `GET /api/health`
  повертає `has_data`.
- **Data safety** — one-click експорт усіх даних (JSON/CSV, `GET /api/export/all`)
  і видалення з попередженням (`DELETE /api/data?confirm=DELETE`).
- **A11y** — aria-labels на інтерактивних елементах, `aria-live` статуси,
  видимий фокус клавіатури, контраст WCAG AA (перевіряється тестами).
- **Packaging** — `pyproject.toml` (PEP 621), console-script `climate-canvas`,
  `pip install -e .` працює.
- **Документація** — `README.en.md` (англійське дзеркало), `INSTALL.md`
  (Windows autostart, Linux systemd user unit, оновлення).
- **Open-source hygiene** — `CONTRIBUTING.md`, `SECURITY.md`, шаблони issue
  (UA+EN), аудит приватності тестами (без приватних шляхів/токенів у git).

## [0.4.0] — 2026-11-05

### Додано
- **Точка роси + ризик цвілі**: психрометрична формула Магнуса (`app/climate.py`);
  точка роси та індикатор ризику цвілі (RH ≥ 70 % при T < 20 °C — «високий»)
  на картках кімнат і в тепловій мапі (нові метрики `dew_point` та `mold_risk`).
- **Порівняння з вулицею**: температура зовні через Open-Meteo Archive API
  (безкоштовно, без ключа) за lat/lon з конфігу (`LATITUDE`/`LONGITUDE`);
  пунктирний оверлей «Зовні» на таймлайні температури; `/api/outdoor` з годинним кешем.
- **Прогноз на 48 год**: Open-Meteo Forecast API — окрема крива майбутнього
  на таймлайні (чекбокс «Прогноз 48 год»); `/api/forecast`.
- **Тижневий звіт**: сторінка `/report` — SVG-графік денних середніх по кімнатах
  + таблиця середнє/мін/макс/вологість; `/api/report/weekly`.
- **PWA manifest** (`/static/manifest.webmanifest`) + SVG-іконка, theme-color.
- **Загальне**: CHANGELOG.md, `.github/FUNDING.yml` (GitHub Sponsors),
  favicon + OG-мета теги, `scripts/smoke.sh` (smoke-тест ендпоінтів), README
  «Чому це існує».

## [0.3.0] — 2026-10

### Додано
- **Енергія (kWh)**: окрема вкладка зі стовпчиковою діаграмою kWh/день,
  сумарним споживанням і вартістю (ціна — поле в UI або `ENERGY_PRICE`).
- **Мітки на таймлайні**: клік по графіку створює анотацію («відкрито вікно»),
  зберігається в SQLite, малюється вертикальною пунктирною лінією.
- **CO₂ / VOC**: сенсори якості повітря (ppm / ppb) у таймлайні та на картках.
- **Темна/світла тема**: перемикач ☀️/🌙, CSS-змінні, теми для Chart.js.

## [0.2.0] — 2026-09

### Додано
- **Експорт CSV** — `GET /api/export/csv` з сирими щогодинними точками кешу.
- **Авто-виявлення сенсорів** — сторінка `/settings`, групування по areas,
  збереження мапінгу в `rooms.json`.
- **Теплова мапа вологості** — перемикач метрики температура/вологість.
- **FastAPI lifespan** замість застарілого `on_event`.

## [0.1.0] — 2026-08

### Додано
- Перший реліз: 4 вьюхи (кімнати, таймлайн, теплова мапа, сезони),
  demo-режим + Home Assistant REST API, SQLite-кеш, щогодинний фон-пул,
  комфорт-зони, тести pytest.
