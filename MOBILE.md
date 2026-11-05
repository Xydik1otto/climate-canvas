# 📱 Мобільні застосунки / Mobile apps

Climate Canvas має мобільну оболонку на **Capacitor 6** — для Android та iOS.
Важливо розуміти архітектуру: нативний застосунок — це **тонка оболонка**, а не
окрема копія застосунку. Вона показує splash-екран, де ви вводите адресу
**вашого власного** climate-canvas сервера, і далі WebView працює з UI, який
обслуговує ваш сервер. Дані не залишають вашу інфраструктуру.

> 🇬🇧 English version below.

---

## 🇺🇦 Android

### Встановлення (sideload, безкоштовно)

1. Відкрийте [Releases](https://github.com/Xydik1otto/climate-canvas/releases)
   (або вкладку Artifacts останнього запуску
   [android-build](https://github.com/Xydik1otto/climate-canvas/actions/workflows/android-build.yml)).
2. Скачайте `app-debug.apk`.
3. На телефоні дозвольте «Встановлення невідомих застосунків» для вашого
   браузера/файлового менеджера (Налаштування → Безпека) і встановіть APK.
4. Відкрийте Climate Canvas, введіть адресу сервера (наприклад
   `http://192.168.1.10:8000`) і натисніть «Підключитися».

Адреса запам'ятовується; splash з'являється лише щоразу, поки ви не підключилися.

### Демо-режим

Кнопка «📦 Демо-режим» на splash відкриває застосунок на вашому сервері з
хешем `#demo`: якщо сервер працює в демо-режимі без історії, детерміновані
демо-дані засіюються автоматично. Зручно показати застосунок друзям без
Home Assistant.

### Збірка локально

```bash
npm install
npx cap add android      # уже виконано — платформа в репозиторії
npx cap sync android
cd android && ./gradlew assembleDebug
# → android/app/build/outputs/apk/debug/app-debug.apk
```

Параметри: minSdk 24 (Android 7.0) → targetSdk 35 (Android 16); єдиний дозвіл —
`INTERNET`.

## 🇺🇦 iOS

**Чесне обмеження:** поширення в App Store вимагає Apple Developer ($99/рік) —
цього немає в бюджеті проєкту. Шлях: **unsigned IPA** з GitHub Actions →
встановлення через AltStore або Sideloadly (безкоштовно, потребує re-sign
кожні 7 днів) або TestFlight у майбутньому.

1. Відкрийте [Actions → ios-build](https://github.com/Xydik1otto/climate-canvas/actions/workflows/ios-build.yml),
   скачайте артефакт `climate-canvas-unsigned-ios` (zip із `.app`).
2. На комп'ютері з macOS: `xcodebuild`-подібний re-sign або простіше —
   [AltStore](https://altstore.io)/[Sideloadly](https://sideloadly.io):
   підключіть iPhone, оберіть zip/`.app`, увійдіть звичайним Apple ID, встановіть.
3. iOS: Налаштування → Основні → VPN і керування пристроями → довіряйте
   своєму Apple ID.
4. Запустіть застосунок, введіть адресу сервера.

Мінімальна версія: iOS 14. ATS послаблено (`NSAllowsArbitraryLoads`), щоб
працювали http-сервери в LAN і через Tailscale.

## 🌍 Віддалений доступ: Tailscale

Цей застосунок **особливо цінний разом із Tailscale** — моніторинг дому
звідусіль:

1. Встановіть Tailscale (безкоштовно до 100 пристроїв) на сервер, де крутиться
   climate-canvas, і на телефон.
2. Адреса сервера для splash — Tailscale-ім'я машини, наприклад
   `http://home-server:8000` ( або MagicDNS-ім'я `http://home-server.tailnet-name.ts.net`).
3. Тепер-home — у кишені: температура, вологість, точка роси, ризик цвілі,
   енергія — з відпустки, з роботи, з магазину. Жодних портів, пробросів чи
   хмарних посередників: трафік іде через WireGuard-тунель напряму.

Альтернативи: WireGuard напряму, reverse-proxy з TLS — будь-що, що віддає
HTTP(S) адресу, яку можна ввести у splash.

## 🛠 CI-збірки

- `android-build.yml`: на кожен push у `mobile/android-ios` — debug APK як
  артефакт (30 днів); на тег `v*` — прикріплюється до Release.
- `ios-build.yml`: на macos-latest — unsigned `.app` → zip артефакт (30 днів).

---

## 🇬🇧 English

### Architecture

The native app is a **thin shell**, not a separate copy: it shows a splash
where you enter the address of **your own** climate-canvas server, and the
WebView then loads the UI served by that server. Your data never leaves your
infrastructure.

### Android install (sideload, free)

1. Grab `app-debug.apk` from
   [Releases](https://github.com/Xydik1otto/climate-canvas/releases) or the
   artifacts of the latest [android-build](https://github.com/Xydik1otto/climate-canvas/actions/workflows/android-build.yml) run.
2. Allow "install unknown apps" for your browser/file manager, install the APK.
3. Open Climate Canvas, enter your server address, tap Connect.

Specs: minSdk 24 (Android 7.0) → targetSdk 35 (Android 16); the only
permission is `INTERNET`.

### Demo mode

The «📦 Demo mode» splash button opens the app on your server with an
`#demo` hash: if the server runs in demo mode with no history yet, the
deterministic demo dataset is seeded automatically.

### iOS install (unsigned, free)

**Honest limitation:** App Store distribution requires Apple Developer
($99/year) — not in the project budget. The path: **unsigned IPA** from
GitHub Actions → install via AltStore or Sideloadly (free, re-sign every
7 days), or TestFlight in the future.

1. Download the `climate-canvas-unsigned-ios` artifact from
   [Actions → ios-build](https://github.com/Xydik1otto/climate-canvas/actions/workflows/ios-build.yml).
2. On a computer: use [AltStore](https://altstore.io) or
   [Sideloadly](https://sideloadly.io) with your regular Apple ID to install.
3. iOS: Settings → General → VPN & Device Management → trust your Apple ID.
4. Launch, enter the server address.

Minimum: iOS 14. ATS is relaxed (`NSAllowsArbitraryLoads`) so plain-http LAN
and Tailscale servers work.

### Remote access: Tailscale

This app is **especially valuable together with Tailscale** — home monitoring
from anywhere:

1. Install Tailscale (free up to 100 devices) on the server running
   climate-canvas and on your phone.
2. Use the Tailscale machine name in the splash, e.g. `http://home-server:8000`
   or `http://home-server.tailnet-name.ts.net`.
3. Your home is now in your pocket: temperature, humidity, dew point, mold
   risk, energy — from vacation, work, or the store. No port forwarding, no
   cloud middlemen: traffic goes through a direct WireGuard tunnel.

Alternatives: plain WireGuard, a reverse proxy with TLS — anything that gives
you an HTTP(S) URL to type into the splash.

### Building locally

```bash
npm install
npx cap sync android && (cd android && ./gradlew assembleDebug)
npx cap sync ios      # build on macOS with Xcode
```

### CI

- `android-build.yml`: debug APK artifact (30-day retention) on every push to
  `mobile/android-ios`; attached to the Release on `v*` tags.
- `ios-build.yml`: unsigned `.app` → zip artifact (30-day retention) on
  macOS runners.
