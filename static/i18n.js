// climate-canvas i18n: UA + EN dictionaries (no other languages by design).
// Auto-detects browser language, persists the choice in localStorage,
// translates [data-i18n] / [data-i18n-ph] / [data-i18n-title] elements and
// exposes I18N.t() for dynamic strings. Dispatches "cc:langchange" so views
// can re-render their dynamic parts.
window.I18N = {
  lang: null,
  dicts: {
    uk: {
      // nav
      nav_rooms: "Кімнати", nav_timeline: "Таймлайн", nav_heatmap: "Теплова мапа",
      nav_seasons: "Сезони", nav_energy: "Енергія",
      report_link_title: "Тижневий звіт", settings_link_title: "Налаштування сенсорів",
      theme_title: "Світла/темна тема", lang_title: "Мова інтерфейсу",
      demo_banner: "Схоже, це перший запуск — історії ще немає. Завантажити демо-дані, щоб побачити всі вьюхи?",
      demo_btn: "📦 Завантажити демо", demo_later: "Ні, дякую",
      // timeline / heatmap / seasons controls
      metric_temperature: "Температура", metric_humidity: "Вологість",
      metric_co2: "CO₂", metric_voc: "VOC",
      metric_dew_point: "Точка роси", metric_mold_risk: "Ризик цвілі",
      days_7: "7 днів", days_30: "30 днів", days_90: "90 днів",
      forecast_label: "Прогноз 48 год", tl_hint: "Клікніть по графіку, щоб додати мітку (відкрито вікно, відпустка…)",
      energy_price: "Ціна kWh:",
      // room cards
      card_humidity: "💧 {v}% · вологість {lo}–{hi}% · T {tlo}–{thi}°C",
      dew_point_line: "🌡 Точка роси: {v}°C",
      mold_line: "⚠️ Цвіль: {level}", mold_title: "RH ≥ 70% при T < 20°C — високий ризик",
      mold_low: "низький", mold_medium: "середній", mold_high: "високий",
      // timeline datasets / annotations
      outside_label: "Зовні (Open-Meteo)", forecast_48: "Прогноз 48 год",
      ann_prefix: "Мітки: ", ann_prompt: "Мітка (напр. «відкрито вікно»):", ann_delete: "видалити",
      dataset_label: "{room} · {metric}",
      // heatmap legend
      legend_humidity: "Сухо {bar} Вологo · {n} днів",
      legend_temp: "Холодно {bar} Спекотно · {n} днів",
      legend_risk: "Ризик цвілі: низький · середній · високий · {n} днів",
      no_data_cell: "немає даних",
      // seasons
      seasons_title: "Середня {metric}, {month}",
      month_1: "січень", month_2: "лютий", month_3: "березень", month_4: "квітень",
      month_5: "травень", month_6: "червень", month_7: "липень", month_8: "серпень",
      month_9: "вересень", month_10: "жовтень", month_11: "листопад", month_12: "грудень",
      // energy
      energy_total: "Всього: {kwh} kWh · ≈ {cost} (за {price}/kWh) · {room}, {days} дн.",
      kwh_day: "kWh/день · {room}",
      // report page
      report_title: "Тижневий звіт", report_back: "Дашборд", report_loading: "Завантаження…",
      report_none: "Немає даних за останні 7 днів.",
      report_generated: "Дані за останні {days} днів · згенеровано {gen}",
      th_room: "Кімната", th_avg: "Середня", th_min: "Мін", th_max: "Макс",
      th_hum: "Вологість (сер.)", th_points: "Точок",
      export_head: "Експорт", pdf_btn: "⬇️ Завантажити PDF", pdf_btn_aria: "Завантажити тижневий звіт у PDF",
      email_head: "Надіслати на email (опційно)",
      email_hint: "SMTP-налаштування зберігаються локально у data/settings.json.",
      em_to: "Кому", em_host: "SMTP-сервер", em_port: "Порт", em_user: "Користувач",
      em_pass: "Пароль", em_from: "Від (From)", em_tls: "TLS (STARTTLS)",
      em_save: "💾 Зберегти SMTP", em_send: "✉️ Надіслати звіт",
      smtp_saved: "✅ SMTP-налаштування збережено.", email_sending: "⏳ Формую PDF і надсилаю…",
      email_sent: "✅ Звіт надіслано на {to}.", fail: "❌ {err}",
      pass_saved_ph: "•••••••• (збережено {hint})",
      // settings page
      setup_head: "🏠 Home Assistant — підключення",
      setup_hint: "Вкажіть адресу інстансу та довготривалий токен доступу (HA → Профіль → Безпека → Long-Lived Access Tokens). Дані зберігаються у data/settings.json — змінні середовища більше не потрібні.",
      setup_url: "URL інстансу", setup_token: "Токен доступу",
      setup_test: "🔌 Перевірити з'єднання", setup_save: "💾 Зберегти",
      setup_env_note: "Поточні URL/токен задані через змінні середовища — збережіть тут, щоб перевизначити.",
      test_in_progress: "⏳ Перевіряю з'єднання…",
      test_ok: "✅ З'єднання встановлено — знайдено сенсорів: {n}",
      test_fail: "❌ Не вдалося підключитися: {err}",
      setup_need_both: "❌ Вкажіть URL і токен.",
      setup_saved: "✅ Збережено ({hint}).",
      setup_saved_restart: "✅ Збережено. Перезапустіть застосунок, щоб перейти з демо на Home Assistant.",
      sensors_head: "Знайдені сенсори",
      th_area: "Area", th_entity: "Entity", th_name: "Назва", th_metric: "Метрика", th_value: "Значення",
      th_metric2: "humidity_entity",
      sensors_none: "Сенсорів не знайдено",
      mapping_head: "Запропоноване відображення кімнат",
      mapping_hint: "Перевірте/відредагуйте відповідність сенсорів і зони вологості (за замовчуванням 30–50 % — безпечний від цвілі діапазон), потім збережіть у rooms.json.",
      th_hum_min: "Вологість мін %", th_hum_max: "Вологість макс %",
      no_suggestions: "Немає пропозицій",
      save_btn: "💾 Зберегти rooms.json",
      saved_path: "✅ збережено: {path}",
    },
    en: {
      nav_rooms: "Rooms", nav_timeline: "Timeline", nav_heatmap: "Heatmap",
      nav_seasons: "Seasons", nav_energy: "Energy",
      report_link_title: "Weekly report", settings_link_title: "Sensor settings",
      theme_title: "Light/dark theme", lang_title: "Interface language",
      demo_banner: "Looks like the first run — no history yet. Load demo data to explore every view?",
      demo_btn: "📦 Load demo", demo_later: "No thanks",
      metric_temperature: "Temperature", metric_humidity: "Humidity",
      metric_co2: "CO₂", metric_voc: "VOC",
      metric_dew_point: "Dew point", metric_mold_risk: "Mold risk",
      days_7: "7 days", days_30: "30 days", days_90: "90 days",
      forecast_label: "48h forecast", tl_hint: "Click the chart to add a marker (window opened, vacation…)",
      energy_price: "kWh price:",
      card_humidity: "💧 {v}% · humidity {lo}–{hi}% · T {tlo}–{thi}°C",
      dew_point_line: "🌡 Dew point: {v}°C",
      mold_line: "⚠️ Mold: {level}", mold_title: "RH ≥ 70% at T < 20°C — high risk",
      mold_low: "low", mold_medium: "medium", mold_high: "high",
      outside_label: "Outdoor (Open-Meteo)", forecast_48: "48h forecast",
      ann_prefix: "Markers: ", ann_prompt: "Marker (e.g. \"window opened\"):", ann_delete: "delete",
      dataset_label: "{room} · {metric}",
      legend_humidity: "Dry {bar} Humid · {n} days",
      legend_temp: "Cold {bar} Hot · {n} days",
      legend_risk: "Mold risk: low · medium · high · {n} days",
      no_data_cell: "no data",
      seasons_title: "Mean {metric}, {month}",
      month_1: "January", month_2: "February", month_3: "March", month_4: "April",
      month_5: "May", month_6: "June", month_7: "July", month_8: "August",
      month_9: "September", month_10: "October", month_11: "November", month_12: "December",
      energy_total: "Total: {kwh} kWh · ≈ {cost} (at {price}/kWh) · {room}, {days} d",
      kwh_day: "kWh/day · {room}",
      report_title: "Weekly report", report_back: "Dashboard", report_loading: "Loading…",
      report_none: "No data for the last 7 days.",
      report_generated: "Last {days} days · generated {gen}",
      th_room: "Room", th_avg: "Avg", th_min: "Min", th_max: "Max",
      th_hum: "Humidity (avg)", th_points: "Points",
      export_head: "Export", pdf_btn: "⬇️ Download PDF", pdf_btn_aria: "Download the weekly report as PDF",
      email_head: "Email it (optional)",
      email_hint: "SMTP settings are stored locally in data/settings.json.",
      em_to: "To", em_host: "SMTP server", em_port: "Port", em_user: "User",
      em_pass: "Password", em_from: "From", em_tls: "TLS (STARTTLS)",
      em_save: "💾 Save SMTP", em_send: "✉️ Send report",
      smtp_saved: "✅ SMTP settings saved.", email_sending: "⏳ Building PDF and sending…",
      email_sent: "✅ Report sent to {to}.", fail: "❌ {err}",
      pass_saved_ph: "•••••••• (saved {hint})",
      setup_head: "🏠 Home Assistant — connection",
      setup_hint: "Enter your instance URL and a long-lived access token (HA → Profile → Security → Long-Lived Access Tokens). Data is stored in data/settings.json — no environment variables needed.",
      setup_url: "Instance URL", setup_token: "Access token",
      setup_test: "🔌 Test connection", setup_save: "💾 Save",
      setup_env_note: "Current URL/token come from environment variables — save here to override them.",
      test_in_progress: "⏳ Testing connection…",
      test_ok: "✅ Connected — sensors found: {n}",
      test_fail: "❌ Connection failed: {err}",
      setup_need_both: "❌ Provide both URL and token.",
      setup_saved: "✅ Saved ({hint}).",
      setup_saved_restart: "✅ Saved. Restart the app to switch from demo to Home Assistant.",
      sensors_head: "Discovered sensors",
      th_area: "Area", th_entity: "Entity", th_name: "Name", th_metric: "Metric", th_value: "Value",
      th_metric2: "humidity_entity",
      sensors_none: "No sensors found",
      mapping_head: "Suggested room mapping",
      mapping_hint: "Review/edit sensor mapping and humidity zones (default 30–50% — a mold-safe range), then save to rooms.json.",
      th_hum_min: "Humidity min %", th_hum_max: "Humidity max %",
      no_suggestions: "No suggestions",
      save_btn: "💾 Save rooms.json",
      saved_path: "✅ saved: {path}",
    },
  },

  t(key, params) {
    let s = (this.dicts[this.lang] || this.dicts.uk)[key];
    if (s == null) s = this.dicts.uk[key];
    if (s == null) return key;
    if (params) for (const [k, v] of Object.entries(params)) s = s.replaceAll(`{${k}}`, String(v));
    return s;
  },

  apply(root = document) {
    root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = this.t(el.dataset.i18n); });
    root.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = this.t(el.dataset.i18nPh); });
    root.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = this.t(el.dataset.i18nTitle); });
    root.querySelectorAll("[data-i18n-aria]").forEach((el) => { el.setAttribute("aria-label", this.t(el.dataset.i18nAria)); });
  },

  detect() {
    const saved = localStorage.getItem("cc-lang");
    if (saved && saved in this.dicts) return saved;
    const nav = (navigator.language || "en").toLowerCase();
    return nav.startsWith("uk") ? "uk" : "en";
  },

  set(lang) {
    if (!(lang in this.dicts)) lang = "uk";
    this.lang = lang;
    localStorage.setItem("cc-lang", lang);
    document.documentElement.lang = lang;
    this.apply();
    const btn = document.querySelector("#lang-toggle");
    if (btn) btn.textContent = lang === "uk" ? "EN" : "UA";
    document.dispatchEvent(new CustomEvent("cc:langchange", { detail: { lang } }));
  },

  init() {
    this.set(this.detect());
    const btn = document.querySelector("#lang-toggle");
    if (btn) btn.addEventListener("click", () => this.set(this.lang === "uk" ? "en" : "uk"));
  },
};

window.I18N.init();
