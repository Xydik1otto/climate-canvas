# Security Policy · Політика безпеки

🇺🇦

## Що робити, якщо знайшли вразливість

**Не створюйте публічний issue з деталями вразливості.** Напишіть власнику
проєкту через GitHub (контакти в профілі) — відповімо і виправимо.

## Ключові правила безпеки проєкту

- **`HASS_TOKEN` і паролі SMTP ніколи не мають потрапити в git.** Вони живуть:
  - у змінних середовища (`HASS_TOKEN`, `HASS_URL`), або
  - у `data/settings.json`, який створює setup-майстер в UI (папка `data/`
    повністю в `.gitignore`).
- Якщо ви випадково опублікували токен — **відкличте його** в Home Assistant
  (Профіль → Безпека → Long-Lived Access Tokens) і створіть новий.
- У issues не публікуйте: токени, паролі, внутрішні URL вашого HA, реальні
  координати помешкання. Приклади URL (`http://homeassistant.local:8123`) — ок.
- Дані користувача локальні: SQLite-кеш і налаштування лежать у `data/` і нікуди
  не надсилаються (єдиний зовнішній виклик — Open-Meteo для погоди, без ключів).

## 🇬🇧

## Reporting a vulnerability

**Do not open a public issue with vulnerability details.** Contact the project
owner via GitHub (see profile contacts) — we will respond and fix it.

## Project security ground rules

- **`HASS_TOKEN` and SMTP passwords must never end up in git.** They live in
  environment variables (`HASS_TOKEN`, `HASS_URL`) or in `data/settings.json`
  created by the UI setup wizard (`data/` is fully git-ignored).
- If you accidentally published a token — **revoke it** in Home Assistant
  (Profile → Security → Long-Lived Access Tokens) and create a new one.
- Never post in issues: tokens, passwords, your internal HA URLs, real home
  coordinates. Example URLs (`http://homeassistant.local:8123`) are fine.
- User data is local: the SQLite cache and settings live in `data/` and are sent
  nowhere (the only external call is Open-Meteo for weather, keyless).
