"""Tests for the weekly report PDF export (reportlab) and optional email."""
import io
from email import message_from_bytes

import pytest

from app import config, report_pdf

SAMPLE_REPORT = {
    "days": 7,
    "rooms": {
        "Living Room": {"avg": 21.5, "min": 19.2, "max": 23.9, "samples": 168,
                        "humidity_avg": 43.7, "daily": [["2026-11-01", 21.1]]},
        "Bedroom": {"avg": 20.1, "min": 18.0, "max": 22.5, "samples": 168,
                    "humidity_avg": None, "daily": [["2026-11-01", 20.0]]},
    },
}


def test_build_pdf_magic_and_size():
    pdf = report_pdf.build_pdf(SAMPLE_REPORT)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_build_pdf_empty_report():
    pdf = report_pdf.build_pdf({"days": 7, "rooms": {}})
    assert pdf.startswith(b"%PDF")


def test_build_pdf_many_rooms_no_crash():
    rooms = {f"Room {i}": {"avg": 20.0 + i, "min": 18.0, "max": 24.0, "samples": 168,
                           "humidity_avg": 45.0, "daily": []} for i in range(40)}
    pdf = report_pdf.build_pdf({"days": 7, "rooms": rooms})
    assert pdf.startswith(b"%PDF")


def test_weekly_pdf_endpoint(client):
    r = client.get("/api/report/weekly.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert "attachment" in r.headers["content-disposition"]
    assert "climate-canvas-weekly-" in r.headers["content-disposition"]
    body = r.content
    assert body.startswith(b"%PDF")
    assert len(body) > 1000


def test_weekly_json_endpoint_unchanged(client):
    data = client.get("/api/report/weekly").json()
    assert data["days"] == 7
    assert set(data["rooms"]) == set(config.DEFAULT_ROOMS)


def test_build_email_message_contains_pdf_attachment():
    msg = report_pdf.build_email_message(b"%PDF-1.7 fake", to="user@example.com", sender="cc@example.com")
    assert msg["To"] == "user@example.com"
    assert msg["From"] == "cc@example.com"
    parsed = message_from_bytes(msg.as_bytes())
    attachments = [p for p in parsed.walk() if p.get_content_type() == "application/pdf"]
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "climate-canvas-weekly.pdf"
    payload = attachments[0].get_payload(decode=True)
    assert payload.startswith(b"%PDF")


class FakeSMTP:
    """Records the SMTP conversation instead of talking to a server."""
    last = None

    def __init__(self, host, port, timeout=None):
        FakeSMTP.last = self
        self.host, self.port = host, port
        self.tls = False
        self.logged_in = None
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)


@pytest.fixture
def fake_smtp(monkeypatch):
    monkeypatch.setattr(report_pdf.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def test_send_email_uses_smtp_and_attaches_pdf(fake_smtp):
    cfg = {"host": "smtp.example.com", "port": 465, "user": "me@example.com",
           "password": "pass", "tls": False, "from": "cc@example.com"}
    report_pdf.send_email(cfg, "you@example.com", b"%PDF fake")
    smtp = fake_smtp.last
    assert smtp.host == "smtp.example.com"
    assert smtp.port == 465
    assert smtp.tls is False
    assert smtp.logged_in == ("me@example.com", "pass")
    assert len(smtp.sent) == 1
    assert smtp.sent[0]["To"] == "you@example.com"


def test_send_email_tls_and_no_login_by_default(fake_smtp):
    report_pdf.send_email({"host": "smtp.example.com"}, "you@example.com", b"%PDF fake")
    smtp = fake_smtp.last
    assert smtp.tls is True
    assert smtp.logged_in is None


def test_email_endpoint_with_overrides(client, fake_smtp):
    r = client.post("/api/report/email", json={
        "to": "you@example.com",
        "smtp_host": "smtp.example.com", "smtp_port": 587,
        "smtp_user": "u@example.com", "smtp_password": "p",
        "smtp_from": "cc@example.com",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["to"] == "you@example.com"
    assert fake_smtp.last.sent[0]["To"] == "you@example.com"


def test_email_endpoint_uses_saved_smtp(client, fake_smtp):
    client.post("/api/smtp", json={"smtp_host": "saved.example.com", "smtp_port": 25,
                                   "smtp_from": "cc@example.com", "smtp_tls": False})
    r = client.post("/api/report/email", json={"to": "you@example.com"})
    assert r.status_code == 200
    assert fake_smtp.last.host == "saved.example.com"
    assert fake_smtp.last.port == 25


def test_email_endpoint_without_host_400(client):
    r = client.post("/api/report/email", json={"to": "you@example.com"})
    assert r.status_code == 400
    assert "SMTP" in r.json()["detail"]


def test_email_endpoint_bad_address_422(client):
    r = client.post("/api/report/email", json={"to": "not-an-email", "smtp_host": "h"})
    assert r.status_code == 422


def test_email_endpoint_smtp_failure_502(client, monkeypatch):
    class BoomSMTP(FakeSMTP):
        def send_message(self, msg):
            raise ConnectionRefusedError("refused")

    monkeypatch.setattr(report_pdf.smtplib, "SMTP", BoomSMTP)
    r = client.post("/api/report/email", json={"to": "you@example.com", "smtp_host": "h"})
    assert r.status_code == 502
    assert "refused" in r.json()["detail"]


def test_smtp_settings_roundtrip_masked(client):
    client.post("/api/smtp", json={"smtp_host": "smtp.example.com", "smtp_port": 587,
                                   "smtp_user": "u@example.com", "smtp_password": "hunter2"})
    data = client.get("/api/smtp").json()
    assert data["host"] == "smtp.example.com"
    assert data["port"] == 587
    assert data["password_set"] is True
    assert data["password_hint"].endswith("er2")
    assert "hunter2" not in client.get("/api/smtp").text


def test_smtp_save_rejects_bad_port(client):
    r = client.post("/api/smtp", json={"smtp_host": "h", "smtp_port": "abc"})
    assert r.status_code == 422


def test_smtp_save_empty_body_422(client):
    r = client.post("/api/smtp", json={})
    assert r.status_code == 422


def test_build_pdf_matches_json_report_values():
    import base64
    import re
    import zlib

    pdf = report_pdf.build_pdf(SAMPLE_REPORT)
    # reportlab compresses text streams (ASCII85 + Flate); decode and check values
    text = b""
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.DOTALL):
        raw = m.group(1).strip()
        try:
            if raw.endswith(b"~>"):
                raw = base64.a85decode(raw, adobe=True)
            text += zlib.decompress(raw)
        except (zlib.error, ValueError):
            text += m.group(1)
    assert b"Living Room" in text
    assert b"21.5" in text
    assert b"43.7" in text
