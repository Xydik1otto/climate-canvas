# Contributing to climate-canvas · Внесок у проєкт

🇺🇦 Дякуємо, що хочете допомогти! Короткі правила — нижче.
🇬🇧 Thank you for helping! The short rules are below.

## 🇺🇦 Як допомогти

1. **Питання/ідеї** → відкрийте Issue з шаблоном «Feature request».
2. **Баги** → шаблон «Bug report»: версія, кроки відтворення, очікуване/фактичне.
   ⚠️ Ніколи не вставляйте в issue реальні токени, паролі чи URL вашого HA.
3. **Pull requests**:
   - одна фіча/фікса = один PR;
   - додайте або оновіть pytest-тести (кожна фіча покрита тестами);
   - `python -m pytest` має бути зеленим локально;
   - UI-рядки — українською та англійською (`static/i18n.js`); **російську
     локалізацію не додавати** — це свідоме рішення власника проєкту;
   - не комітьте `data/` (там токен і кеш), `.env`, `rooms.json`.
4. **Стиль коду**: без зайвих залежностей; бекенд — стандартна бібліотека +
   FastAPI/httpx/reportlab; фронтенд — без build-кроку (vanilla JS).

Перед великими змінами відкрийте issue і обговоріть підхід.

## 🇬🇧 How to help

1. **Questions/ideas** → open an Issue using the «Feature request» template.
2. **Bugs** → the «Bug report» template: version, steps to reproduce, expected/actual.
   ⚠️ Never paste real tokens, passwords, or your HA URL into issues.
3. **Pull requests**:
   - one feature/fix = one PR;
   - add or update pytest tests (every feature is test-covered);
   - `python -m pytest` must be green locally;
   - UI strings go into both UA and EN (`static/i18n.js`); **do not add Russian
     localization** — this is a deliberate decision by the project owner;
   - never commit `data/` (token + cache), `.env`, `rooms.json`.
4. **Code style**: no extra dependencies; backend = stdlib + FastAPI/httpx/reportlab;
   frontend = no build step (vanilla JS).

For larger changes, open an issue first and discuss the approach.
