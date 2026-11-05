"""Тижневий звіт у self-contained HTML (для вкладення чи HTML-листа).

`build_html` — чиста функція (dict → str), без зовнішніх ресурсів:
усі стилі інлайн, тож файл/лист виглядає однаково в будь-якому клієнті.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

HEADINGS = {
    "uk": "climate-canvas — тижневий звіт",
    "en": "climate-canvas — weekly report",
}

_CSS = (
    "body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1c2733;"
    "margin:24px}"
    "h1{font-size:18px;margin:0 0 4px}"
    ".meta{color:#6b7a88;font-size:12px;margin-bottom:16px}"
    "table{border-collapse:collapse;width:100%;max-width:640px;font-size:14px}"
    "th,td{border:1px solid #d7dee5;padding:6px 10px;text-align:right}"
    "th:first-child,td:first-child{text-align:left}"
    "th{background:#eef3f7}"
    ".empty{color:#6b7a88;font-style:italic}"
)


def build_html(report: dict, lang: str = "uk") -> str:
    """Відрендерити тижневий звіт (з /api/report/weekly) як HTML-рядок."""
    title = HEADINGS.get(lang, HEADINGS["uk"])
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rooms: dict[str, dict[str, Any]] = report.get("rooms", {})

    if rooms:
        rows = []
        for room, r in rooms.items():
            hum = r.get("humidity_avg")
            cells = [
                html.escape(str(room)),
                str(r.get("avg", "—")),
                str(r.get("min", "—")),
                str(r.get("max", "—")),
                "—" if hum is None else str(hum),
                str(r.get("samples", 0)),
            ]
            rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        head = "<tr><th>Кімната</th><th>Середня °C</th><th>Мін °C</th>" \
               "<th>Макс °C</th><th>Вологість %</th><th>Вимірів</th></tr>"
        body = f"<table>{head}{''.join(rows)}</table>"
    else:
        body = '<p class="empty">Немає даних за останні 7 днів.</p>'

    return (
        "<!DOCTYPE html>\n"
        '<html lang="uk"><head><meta charset="utf-8">'
        "<title>climate-canvas — тижневий звіт</title>"
        f"<style>{_CSS}</style></head><body>"
        f"<h1>{html.escape(title)}</h1>"
        f'<p class="meta">{report.get("days", 7)} днів · згенеровано {generated}</p>'
        f"{body}</body></html>\n"
    )
