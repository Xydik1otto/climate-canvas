// Climate Canvas mobile splash: save the user's server address, then hand
// the WebView over to that server's UI. localStorage persists across launches.
'use strict';

const KEY = 'cc-server-url';
const $ = (sel) => document.querySelector(sel);

const I18N = {
  uk: {
    invalid: 'Введіть адресу сервера, наприклад https://climate.example.ts.net',
  },
  en: {
    invalid: 'Enter the server address, e.g. https://climate.example.ts.net',
  },
};

const lang = (navigator.language || 'en').toLowerCase().startsWith('uk') ? 'uk' : 'en';

function translate() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    const dict = {
      uk: {
        tagline: 'Моніторинг клімату дому — ваш власний сервер',
        url_label: 'Адреса вашого climate-canvas сервера',
        hint: 'Наприклад: http://192.168.1.10:8000 або адреса Tailscale. Сервер має бути запущений заздалегідь.',
        connect: 'Підключитися',
        demo: '📦 Демо-режим',
        demo_hint: 'Демо-режим відкриє застосунок на вашому сервері з детермінованими демо-даними (потрібен запущений сервер — він запропонує завантажити демо сам).',
      },
      en: {
        tagline: 'Home climate monitoring — your own server',
        url_label: 'Address of your climate-canvas server',
        hint: 'For example: http://192.168.1.10:8000 or a Tailscale address. The server must already be running.',
        connect: 'Connect',
        demo: '📦 Demo mode',
        demo_hint: 'Demo mode opens the app on your server with deterministic demo data (needs a running server — it will offer to seed the demo itself).',
      },
    }[lang];
    if (dict[key]) el.textContent = dict[key];
  });
}

function normalizeUrl(raw) {
  let v = (raw || '').trim();
  if (!v) return null;
  if (!/^https?:\/\//i.test(v)) v = 'https://' + v;
  try {
    const u = new URL(v);
    if (!u.hostname) return null;
    return u.origin + (u.pathname === '/' ? '' : u.pathname.replace(/\/$/, ''));
  } catch {
    return null;
  }
}

function showError(msg) {
  const el = $('#error');
  el.textContent = msg;
  el.hidden = false;
}

function connect(demo) {
  const url = normalizeUrl($('#server-url').value) || localStorage.getItem(KEY);
  if (!url) { showError(I18N[lang].invalid); return; }
  localStorage.setItem(KEY, url);
  // #demo: the server's UI picks this up and seeds deterministic demo data.
  window.location.href = url + (demo ? '/#demo' : '/');
}

$('#connect-btn').addEventListener('click', () => connect(false));
$('#demo-btn').addEventListener('click', () => connect(true));
$('#server-url').addEventListener('keydown', (e) => { if (e.key === 'Enter') connect(false); });

$('#server-url').value = localStorage.getItem(KEY) || '';
translate();
