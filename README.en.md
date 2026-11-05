# climate-canvas

![tests](https://github.com/bigpi/climate-canvas/actions/workflows/tests.yml/badge.svg)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![version](https://img.shields.io/badge/version-1.0.0-blue)

**[🇺🇦 Українська версія](README.md)**

**Home Climate & Energy Canvas** — long-term visualization of temperature, humidity,
CO₂/VOC and energy from Home Assistant.

## Why this exists

This dashboard was born from real, confirmed Home Assistant user pain — the data
is there, but the long-term picture is missing:

> «The current statistics graph in Home Assistant is suboptimal. … Better graphical
> representations of temperature/humidity changes over time are needed.»
> — discussion on community.home-assistant.io (feature requests)

Additional voices from the same threads:

- users complain the built-in graphs «show only 24h» and don't let you compare
  season with season or find out *when exactly* the home got damp;
- people learn about condensation and mold after the fact — when there is already
  frost on the window, although the sensors should have warned a week earlier.

climate-canvas closes exactly this gap: a local, lightweight (FastAPI + Chart.js,
no cloud, no Docker) dashboard that keeps history for as long as you like and
shows it the way humans read it — room cards, timelines, «day × hour» heatmaps,
dew point, outdoor comparison, forecast and a weekly PDF report.

## The problem

Home Assistant collects data beautifully but shows long horizons poorly:

- The official Home Assistant blog admits that statistics graphs with legends are
  «suboptimal».
- The community complains that statistics graphs are limited; sensor owners want
  «better graphical representations of temperature/humidity changes over time».
- House-wide heatmaps (day × hour per room) simply don't exist in the standard UI.

## Solution (v1.0.0)

A lightweight local web dashboard: Python FastAPI backend + plain HTML/JS/Chart.js
frontend (CDN, no build step). Data comes from the Home Assistant REST API or from
a deterministic demo generator.

### Views

1. **Room card grid** — current temperature/humidity per room with temperature
   comfort zones and configurable per-room humidity zones (default 30–50 %).
2. **Timeline** — 7/30/90-day chart with day/night shading, outdoor overlay and
   a 48h forecast continuation.
3. **Heatmap** — «days × hours» matrix with metric switch: temperature, humidity,
   **dew point** and **mold risk**.
4. **Seasons** — compare the same month across years.

### What's new in v1.0.0

- **Home Assistant setup wizard** — `/settings` page: instance URL + long-lived
  access token with a **Test connection** button; saved to `data/settings.json`
  (environment variables still work, the wizard takes priority).
- **Per-room humidity comfort zones** — `humidity_min`/`humidity_max` in
  `rooms.json`, editable in the settings UI; room cards color-code humidity
  against the zone.
- **Weekly report as PDF** — `/api/report/weekly.pdf` (reportlab) with an
  **optional email delivery** via SMTP (`/api/report/email`), settings form on
  the `/report` page.
- **UA/EN interface** — full i18n of the UI with a language switcher, browser
  language auto-detection and a persisted choice. By design there is no Russian
  localization.
- **First-run experience** — a fresh demo install shows an opt-in
  «📦 Load demo» banner; demo history is seeded only when you ask for it.
- **Data safety** — one-click export of everything (JSON/CSV,
  `GET /api/export/all`) and a deletion flow that warns first and requires an
  explicit confirmation.
- **Accessibility** — aria-labels on interactive elements, `aria-live` status
  regions, visible keyboard focus, WCAG AA contrast (asserted by tests).
- **Packaging** — `pip install -e .` and a `climate-canvas` console command.

### Earlier highlights

- **CSV export** per room/metric; **sensor auto-discovery** grouped by area.
- **Energy (kWh)** view with cost estimate; **CO₂/VOC** sensors.
- **Timeline annotations** («window opened», «vacation») stored in SQLite.
- **Dew point** (Magnus formula) and **mold risk** (high: RH ≥ 70 % at T < 20 °C).
- **Outdoor temperature** and **48h forecast** via Open-Meteo (free, no API key).
- **Weekly report** page with a pure-SVG chart; **PWA manifest** so the dashboard
  can be installed on a phone/desktop; dark/light theme.

## Data sources

- **Home Assistant REST API**: `/api/states` and `/api/history/period`.
  The easiest way to connect is the **setup wizard** on the `/settings` page
  (URL + token, «Test connection» button, stored in `data/settings.json`).
  Environment variables still work: `HASS_TOKEN` for the token, `HASS_URL` for
  the base URL (default `http://supervisor/core/api`, alternative
  `http://homeassistant.local:8123`); the wizard takes priority over env.
- **Demo mode** — deterministic synthetic data so everything works without HA.
  Enabled with `DEMO=1` or automatically when no token is configured; on the
  first run demo history is loaded with the «📦 Load demo» button.

### Getting a HASS_TOKEN

1. In Home Assistant: Profile → Security → **Long-Lived Access Tokens** → Create Token.
2. Either paste it into the setup wizard (`/settings`), or pass it via env:

```bash
export HASS_TOKEN="your_long_lived_token"
export HASS_URL="http://homeassistant.local:8123"   # or the supervisor URL on HA OS
python -m uvicorn app.main:app
```

Without a token the app starts in demo mode — no real HA needed.

## Quick start

> 📘 A step-by-step guide for non-programmers (Windows autostart, systemd,
> updating) lives in [INSTALL.md](INSTALL.md).

```bash
cd climate-canvas
pip install -e .          # or: pip install -r requirements.txt
climate-canvas            # http://127.0.0.1:8321

# demo mode (no Home Assistant)
python -m uvicorn app.main:app --reload
# or with a real HA (env works, but the /settings wizard is enough):
export HASS_TOKEN=your_long_lived_token
export HASS_URL=http://homeassistant.local:8123
python -m uvicorn app.main:app --reload

# tests
pytest
```

Open http://127.0.0.1:8321 — the dashboard with Rooms / Timeline / Heatmap /
Seasons / Energy tabs; sensor settings live at http://127.0.0.1:8321/settings.

## Screenshots

> TODO: add real screenshots (demo mode makes them reproducible).

![Room cards](docs/screenshots/rooms.png)
![Timeline](docs/screenshots/timeline.png)
![Heatmap](docs/screenshots/heatmap.png)
![Seasons](docs/screenshots/seasons.png)

## Cache

SQLite (`data/cache.db`) keeps the long history; the backend pulls new data from
HA once an hour (in demo mode the cache is filled by the generator on request).

## Performance

Hot paths are profiled (cProfile, `scripts/profile_hot.py`) and optimized with
zero change to any API number (a regression test pins the exact expected
values — `tests/test_regression_perf.py`). Details: [docs/PERFORMANCE.md](docs/PERFORMANCE.md).

| Benchmark (`scripts/bench.py`, 90 days × 4 rooms, median) | Before | After |
|---|---|---|
| Demo generation + cache seeding (`seed_cache`) | 1.11 s | **0.30 s** (~3.7×) |
| Timeline + heatmap aggregation | 0.053 s | **0.044 s** (~1.2×) |
| Full `pytest` run (167→174 tests) | 87.6 s | **13.9 s** (~6.3×) |

`/api/timeline` and `/api/heatmap` aggregates are memoized per
(room, metric, window, data version) — repeat requests within the hour neither
re-read nor re-aggregate SQLite; any write invalidates the cache.

## Status (roadmap)

| Feature | Status |
|---|---|
| 4 core views, demo + HA, cache, tests (MVP) | ✅ |
| Lifespan, CSV export, sensor auto-discovery, humidity heatmap (v0.1.0-alpha) | ✅ |
| Energy kWh + cost, timeline annotations, CO₂/VOC, theme (v0.3.0) | ✅ |
| Dew point + mold risk, outdoor temperature (Open-Meteo), 48h forecast, weekly report, PWA manifest (v0.4.0) | ✅ |
| HA setup wizard, per-room humidity zones, PDF report + email, UA/EN i18n, first-run demo button, INSTALL.md, packaging, full export, a11y (**v1.0.0**) | ✅ |
| «this week vs last week», push notifications for mold risk | ⏳ |

## Smoke test

```bash
bash scripts/smoke.sh   # starts a demo server on a random port, checks endpoints, PASS/FAIL
```

## 📱 Mobile apps

A mobile shell (Capacitor 6) for Android and iOS exists: a splash with **your**
server address + demo mode, CI-built APK (sideload), unsigned iOS via AltStore.
Especially valuable with Tailscale — home monitoring from anywhere.
Details: [MOBILE.md](MOBILE.md).

## Contributing

PRs and issues are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md);
report bugs via the templates in `.github/ISSUE_TEMPLATE/`. Security concerns —
see [SECURITY.md](SECURITY.md) (never post tokens in issues).

**Suggested GitHub topics:** `home-assistant`, `smart-home`, `visualization`,
`fastapi`, `open-meteo` (already listed in `pyproject.toml` → `keywords`).

## License

MIT — see [LICENSE](LICENSE). The project is local-first; your data never leaves
your machine.
