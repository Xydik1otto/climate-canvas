"""Weekly report rendering: PDF via reportlab + optional SMTP email.

`build_pdf` is pure (dict in, bytes out) and unit-tested. Email sending is
isolated in `send_email` so tests can stub smtplib.
"""
from __future__ import annotations

import io
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4
MARGIN = 15 * 72 / 25.4  # 15 mm
LINE_H = 16
ROW_H = 18

HEADINGS = {
    "uk": "climate-canvas — тижневий звіт",
    "en": "climate-canvas — weekly report",
}


def build_pdf(report: dict, lang: str = "uk") -> bytes:
    """Render a weekly report dict (from /api/report/weekly) as a PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    title = HEADINGS.get(lang, HEADINGS["uk"])
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    y = PAGE_H - MARGIN
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN, y, title)
    y -= LINE_H
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN, y, f"{report.get('days', 7)} days · generated {generated}")
    y -= LINE_H * 2

    rooms: dict[str, dict[str, Any]] = report.get("rooms", {})
    if not rooms:
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(MARGIN, y, "No data for the last 7 days.")
    else:
        # Header row
        c.setFont("Helvetica-Bold", 10)
        cols = [MARGIN, MARGIN + 140, MARGIN + 200, MARGIN + 260, MARGIN + 320, MARGIN + 390, MARGIN + 460]
        headers = ["Room", "Avg °C", "Min °C", "Max °C", "Hum %", "Samples"]
        for x, h in zip(cols, headers):
            c.drawString(x, y, h)
        y -= ROW_H
        c.setFont("Helvetica", 10)
        for room, r in rooms.items():
            if y < MARGIN + ROW_H:  # page overflow -> new page with a continued header
                c.showPage()
                y = PAGE_H - MARGIN
                c.setFont("Helvetica-Bold", 10)
                for x, h in zip(cols, headers):
                    c.drawString(x, y, h)
                y -= ROW_H
                c.setFont("Helvetica", 10)
            hum = r.get("humidity_avg")
            row = [
                str(room)[:30],
                f"{r.get('avg', '—')}",
                f"{r.get('min', '—')}",
                f"{r.get('max', '—')}",
                "—" if hum is None else f"{hum}",
                f"{r.get('samples', 0)}",
            ]
            for x, cell in zip(cols, row):
                c.drawString(x, y, cell)
            y -= ROW_H

    c.showPage()
    c.save()
    return buf.getvalue()


def build_email_message(pdf_bytes: bytes, to: str, sender: str = "climate-canvas@localhost",
                        subject: str = "climate-canvas — тижневий звіт") -> EmailMessage:
    """Compose a multipart email with the weekly PDF attached (not sent yet)."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content("Тижневий звіт climate-canvas у вкладенні (PDF).\nThe weekly climate-canvas report is attached as PDF.")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                       filename="climate-canvas-weekly.pdf")
    return msg


def send_email(cfg: dict, to: str, pdf_bytes: bytes) -> str:
    """Send the PDF report via SMTP. cfg keys: host, port, user, password, tls, from.

    Returns the message id on success; raises on any SMTP failure.
    """
    msg = build_email_message(pdf_bytes, to=to, sender=cfg.get("from") or "climate-canvas@localhost")
    with smtplib.SMTP(cfg["host"], int(cfg.get("port", 587)), timeout=30) as smtp:
        if cfg.get("tls", True):
            smtp.starttls()
        if cfg.get("user"):
            smtp.login(cfg["user"], cfg.get("password", ""))
        smtp.send_message(msg)
    return msg.get("Message-ID", "")
