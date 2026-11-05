# Встановлення climate-canvas · Installation

## 🇺🇦 Українською

### Що потрібно
- Python 3.11 або новіший ([python.org/downloads](https://www.python.org/downloads/))
- Home Assistant з увімкненим REST API (або нічого — можна подивитися демо)

### Windows (10/11)

1. **Завантажте проєкт**: кнопка **Code → Download ZIP** на GitHub, розпакуйте
   (наприклад, у `C:\climate-canvas`), або `git clone`.
2. **Відкрийте термінал у папці проєкту**: у Провіднику введіть в адресному рядку
   `cmd` (або відкрийте папку в PowerShell).
3. **Встановіть залежності** (один раз):
   ```
   python -m pip install -e .
   ```
4. **Запуск**:
   ```
   climate-canvas
   ```
   і відкрийте в браузері **http://127.0.0.1:8321**

   Або без встановлення:
   ```
   python -m uvicorn app.main:app --port 8321
   ```
5. **Перший запуск**: програма покаже банер «Завантажити демо» — натисніть, щоб
   побачити всі графіки на синтетичних даних. Потім на сторінці **⚙️ Налаштування**
   введіть адресу вашого Home Assistant (наприклад `http://homeassistant.local:8123`)
   і довготривалий токен доступу (HA → Профіль → Безпека → Long-Lived Access
   Tokens). Перевірте кнопкою «Перевірити з'єднання» і збережіть — після
   перезапуску дашборд читатиме реальні сенсори.

#### Автозапуск (Windows)
1. Натисніть `Win + R`, введіть `shell:startup`, Enter.
2. Створіть у папці, що відкрилась, файл `climate-canvas.bat` з рядком:
   ```
   "C:\climate-canvas\.venv\Scripts\climate-canvas.exe"
   ```
   (або повний шлях до `python -m uvicorn ...`). Тепер дашборд стартує разом
   із Windows.

### Linux

1. Клонуйте проєкт і встановіть залежності:
   ```bash
   git clone https://github.com/bigpi/climate-canvas.git
   cd climate-canvas
   python3 -m pip install --user -e .
   ```
2. Створіть systemd user-юніт `~/.config/systemd/user/climate-canvas.service`:
   ```ini
   [Unit]
   Description=climate-canvas dashboard
   After=network-online.target

   [Service]
   ExecStart=%h/.local/bin/climate-canvas --host 0.0.0.0 --port 8321
   Restart=on-failure

   [Install]
   WantedBy=default.target
   ```
3. Увімкніть і запустіть:
   ```bash
   systemctl --user enable --now climate-canvas
   ```
   Дашборд: `http://<IP-сервера>:8321`. Щоб сервіс працював і без входу в
   систему: `sudo loginctl enable-linger $USER`.

### Оновлення
```bash
git pull
python -m pip install -e .
```
і перезапустіть сервіс/ ярлик. Дані (SQLite-кеш, налаштування) у папці `data/`
не чіпаються. Перед великими оновленнями зробіть експорт: **⚙️ Налаштування →
Дані → Експорт усього (JSON)**.

### Де мої дані?
- `data/cache.db` — історія показів (SQLite)
- `data/settings.json` — URL/токен HA та SMTP (ніколи не комітиться)
- `rooms.json` — мапінг сенсорів і зони вологості

---

## 🇬🇧 English

### Requirements
- Python 3.11+ ([python.org/downloads](https://www.python.org/downloads/))
- A Home Assistant instance with the REST API enabled — or nothing at all (demo mode)

### Windows (10/11)

1. **Get the project**: on GitHub press **Code → Download ZIP** and unpack
   (e.g. `C:\climate-canvas`), or `git clone`.
2. **Open a terminal in the project folder** (type `cmd` in the Explorer
   address bar).
3. **Install dependencies** (once):
   ```
   python -m pip install -e .
   ```
4. **Run**:
   ```
   climate-canvas
   ```
   then open **http://127.0.0.1:8321** in your browser.

   Or without installing:
   ```
   python -m uvicorn app.main:app --port 8321
   ```
5. **First run**: you'll see a «Load demo» banner — click it to explore every
   view on synthetic data. Then go to **⚙️ Settings**, enter your Home Assistant
   URL (e.g. `http://homeassistant.local:8123`) and a long-lived access token
   (HA → Profile → Security → Long-Lived Access Tokens). Press «Test connection»
   and save — after a restart the dashboard reads your real sensors.

#### Autostart (Windows)
1. Press `Win + R`, type `shell:startup`, Enter.
2. Create a `climate-canvas.bat` file in the opened folder containing:
   ```
   "C:\climate-canvas\.venv\Scripts\climate-canvas.exe"
   ```

### Linux

1. Clone and install:
   ```bash
   git clone https://github.com/bigpi/climate-canvas.git
   cd climate-canvas
   python3 -m pip install --user -e .
   ```
2. Create a systemd user unit `~/.config/systemd/user/climate-canvas.service`:
   ```ini
   [Unit]
   Description=climate-canvas dashboard
   After=network-online.target

   [Service]
   ExecStart=%h/.local/bin/climate-canvas --host 0.0.0.0 --port 8321
   Restart=on-failure

   [Install]
   WantedBy=default.target
   ```
3. Enable and start:
   ```bash
   systemctl --user enable --now climate-canvas
   sudo loginctl enable-linger $USER   # run without an active login session
   ```
   Dashboard: `http://<server-ip>:8321`.

### Updating
```bash
git pull
python -m pip install -e .
```
then restart the service/shortcut. Your data (`data/`) is never touched.
Before big updates export a backup: **⚙️ Settings → Data → Export everything (JSON)**.

### Where is my data?
- `data/cache.db` — reading history (SQLite)
- `data/settings.json` — HA URL/token and SMTP settings (never committed)
- `rooms.json` — sensor mapping and humidity zones
