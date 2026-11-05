# Contributing to climate-canvas

🇬🇧 Thank you for helping! This document explains how the code is organized,
how to run and test it, and how to add new features.
🇺🇦 Ukrainian version: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🧠 How the project works (where things live)

The app is a thin backend (`app/`, Python + FastAPI) plus a no-build-step
frontend (`static/`, vanilla JS). All climate math lives in the backend;
the frontend only draws.

### `app/ha_client.py` — Home Assistant REST API client

- Pulls `/api/states` from your Home Assistant using the token stored in `data/`
  (never committed to the repo).
- The **parsing functions are pure** (`parse_states` etc.): payload in,
  `{entity_id: {metric: value}}` out. They are unit-tested against recorded
  fixtures, with no network. Network wrappers never raise upward — on failure
  they return empty data so the dashboard stays alive.
- Metrics are recognized by `unit_of_measurement`: `°C` → temperature,
  `%` → humidity, `kWh` → energy, `ppm` → co2, `ppb` → voc.

### `app/climate.py` — psychrometrics: dew point and mold risk

Dew point uses the **Magnus (Magnus-Tetens) formula**, the standard
approximation of the saturation vapor pressure:

```
γ(T, RH) = ln(RH/100) + (a·T) / (b + T)
Td = (b·γ) / (a − γ)
```

where `a = 17.62`, `b = 243.12 °C` (coefficients valid for −40…+50 °C over
water), `T` is air temperature in °C, `RH` is relative humidity in %.

Intuition: the dew point is the temperature you must cool air to before vapor
starts condensing. The closer `Td` is to the actual temperature of a cold
surface (wall, window pane), the higher the risk of condensation and mold.

`mold_risk(T, RH)` is a qualitative scale built on the same quantities:

- `high` — RH ≥ 70 % at T < 20 °C (classic condensation-on-cold-surface zone);
- `medium` — RH ≥ 65 % (approaching the danger zone);
- `low` — everything else.

If you change these thresholds, update both the test and the UI hint
(`mold_title` in i18n).

### `app/openmeteo.py` — outdoor weather

Client for the free Open-Meteo API (no key required): temperature history
(`archive-api`) and a 48-hour forecast (`forecast`). As in `ha_client`,
parsers are pure and tested; fetchers never fail — on network problems they
return an empty series, so the dashboard keeps working offline
(without the "Outdoor" line on charts).

### `app/cache.py` — SQLite history cache + memoized aggregates

- The `readings(room, metric, ts, value)` table keeps the whole long-term
  history locally, so HA is not asked on every click. Plus `annotations`
  for timeline labels.
- Aggregates (`hourly_mean`, `heatmap_matrix`, `hourly_since`, `heatmap_since`)
  are **memoized** in memory by key `(room, metric, since, point count)`.
  Repeated requests to `/api/timeline` and `/api/heatmap` within an hour do
  not re-read the DB.
- Any write clears the cache (`_invalidate`) — the invariant: after a write,
  aggregates are always recomputed from fresh data. If you add a new write
  path to the cache, do not forget invalidation, or the tests will catch it
  (there is a regression test pinning bit-identical aggregates).

### `app/demo_data.py` — determinism is critical for tests

The demo generator produces synthetic but plausible history (90 days ×
rooms × metrics). The key rule: **the same `(room, day)` always produces the
same hourly series**. Determinism rests on:

- stable per-room offsets derived from the room name (`_room_profile`);
- pseudo-noise from `random.Random(f"{room}|{day}|…")` — a seed string, not
  global state;
- `lru_cache` over the noise — an optimization (~3.7× on seed) that
  **does not change values** (pinned by a regression test).

Consequence: tests, screenshots, and benchmarks are reproducible. If you
change the generator's formulas, the series change — the regression test
will tell you loudly.

### Performance experience: `docs/PERFORMANCE.md`

Before "optimizing" anything in `demo_data` / `cache.py`, read
`docs/PERFORMANCE.md` — it documents the full cycle: the symptom
(pytest 87.6 s), cProfile findings (top-3 hot spots), the `scripts/bench.py`
before/after baseline, and what was actually done. Key lessons:

- profile before guessing (`scripts/profile_hot.py`, `pytest --durations=15`);
- `random.Random(str-seed)` per point is the most expensive seed operation;
- one `executemany` beats thousands of individual `INSERT`s;
- memoizing aggregates speeds up repeated requests for free — but **always**
  with invalidation after writes.

---

## 🔧 Environment and tests

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q          # must be green
python -m app.main           # run the server
```

### How to write FAST tests

Every test using the `client` fixture seeds demo history into its own
temporary DB. The full volume (90 days) is ~43,200 points; tests need far less.

- By default the fixture seeds **32 days** (`tests/conftest.py`).
- If your test needs the full volume or a different horizon, override the
  environment variable:

  ```bash
  CLIMATE_CANVAS_TEST_DAYS=90 python -m pytest -q tests/test_cache.py
  ```

- Rules: don't seed data by hand where the fixture suffices; don't raise
  `TEST_DEMO_DAYS` "just in case"; check aggregate tests on small windows
  (7–32 days). The full run must stay within ~15 s.

## ➕ HOW TO ADD A METRIC (the CO₂/VOC example)

This is the most common kind of feature. CO₂ and VOC followed exactly this path:

1. **Parsing** — `app/ha_client.py`, `parse_states`: add unit recognition
   (`ppm` → `co2`, `ppb` → `voc`) to the `unit_of_measurement` loop.
2. **Room config** — `app/config.py`: add the entity field (`co2_entity`,
   `voc_entity`) so the user can bind the sensor in settings.
3. **API** — `app/main.py`: extend the `Query(..., pattern=...)` regexes
   (including `HEAT_METRICS`) and `enrich()`/`/api/rooms` so the metric
   reaches the responses.
4. **Cache** — `app/cache.py` stores any `(room, metric, ts, value)`, so usually
   no changes needed; make sure writes go through `add_readings` (aggregates
   and invalidation work automatically).
5. **UI** — `static/app.js`: timeline lines/heatmap + the metric picker entry.
6. **i18n** — `static/i18n.js`: the `metric_<name>` key in both dictionaries
   (`uk` and `en`) — both at once, not "I'll add English later".
7. **Tests** — a parser unit test with a payload fixture + an endpoint
   integration test via the `client` fixture (demo data has no new metric —
   seed it explicitly in the test).
8. **CHANGELOG.md** — a line under `[Unreleased]`.

## 🌿 Branches

- **`master`** — the stable branch: backend + web UI, green pytest, all
  code/doc changes land here. Every commit must be working.
- **`mobile/android-ios`** — the mobile port (Capacitor 6): `android/`, `ios/`,
  a splash screen with the HA server address setting + a demo-mode button,
  CI builds (`android-build.yml`, `ios-build.yml`), `MOBILE.md`. Maintained
  on top of `master` (regular rebase/merge from master); backend changes are
  made in master and arrive here only via merge — **do not edit the backend
  directly on the mobile branch**.
- New features: short-lived branches off `master` → PR into `master`.

## 🔀 PRs and commits

- One feature/fix = one PR; the commit/PR body explains "why", not "what".
- Add or update pytest tests (every feature is test-covered).
- Commit style: `type: short description` (`feat:`, `fix:`, `test:`, `perf:`,
  `docs:`, `mobile:`, `ci:`). Examples from history: `perf: cache demo noise per (room, day)`,
  `test: client fixture seeds 32 demo days`.
- Never commit `data/` (token + cache), `.env`, `rooms.json`.

## 🌐 i18n

- All UI strings live in `static/i18n.js`, dictionaries `uk` and `en`;
  dynamic strings go through `I18N.t()`.
- In markup, use the `data-i18n` / `data-i18n-ph` / `data-i18n-title` attributes.
- Language is auto-detected from the browser and persisted in `localStorage`.
- **Do not add Russian localization** — this is a deliberate decision by the
  project owner. And no new languages "quickly": open an issue first.

## 🚦 Pre-PR checklist

- [ ] `python -m pytest -q` green (~15 s);
- [ ] new UI strings present in both dictionaries (`uk`, `en`);
- [ ] the aggregates regression test still passes (memoization/determinism intact);
- [ ] CHANGELOG.md updated;
- [ ] no `data/`, tokens, or Russian-localization mentions in the diff.

For larger changes, open an issue first and discuss the approach.
