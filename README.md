# climate-canvas

**Home Climate & Energy Canvas** — довгострокова візуалізація клімату та енергії з Home Assistant.

## Проблема

Home Assistant чудово збирає дані, але погано їх показує на довгих горизонтах:

- Офіційний блог Home Assistant визнає, що графіки з легендами «suboptimal» (неоптимальні).
- Ком'юніті скаржиться, що статистичні графіки обмежені; власники сенсорів хочуть
  «better graphical representations of temperature/humidity changes over time»
  (тренд зі скану 9363 постів).
- Теплових мап будинку (день × година по кімнатах) у стандартному UI взагалі немає.

## Рішення (MVP)

Легкий локальний веб-дашборд: Python FastAPI бекенд + чистий HTML/JS/Chart.js фронтенд
(CDN, без build-кроку). Дані — з Home Assistant REST API або з демо-генератора.

### Вьюхи

1. **Room card grid** — поточні температура/вологість по кімнатах з комфорт-зонами.
2. **Timeline** — графік на 7/30/90 днів із затіненням день/ніч.
3. **Heatmap** — матриця «дні × години», середня температура по кімнатах (SVG).
4. **Seasons** — порівняння сезонів (наприклад, січень 2025 vs січень 2026).

### Джерела даних

- **Home Assistant REST API**: `/api/states` та `/api/history/period`.
  Токен — у змінній середовища `HASS_TOKEN`; базовий URL — `HASS_URL`
  (за замовчуванням `http://supervisor/core/api`, альтернатива
  `http://homeassistant.local:8123`).
- **Demo mode** — детерміновані синтетичні дані, щоб усе працювало без HA.
  Увімкається через `DEMO=1` або автоматично, якщо `HASS_TOKEN` не задано.

### Кеш

SQLite (`data/cache.db`) зберігає довгу історію; бекенд підтягує нові дані
з HA раз на годину (у demo-режимі кеш заповнюється генератором).

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

# тесты
pytest
```

Відкрийте http://127.0.0.1:8000 — дашборд із вкладками Rooms / Timeline / Heatmap / Seasons.

## Ліцензія

MIT (планується). Проєкт локальний, дані не залишають вашої машини.
