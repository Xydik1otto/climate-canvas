"""Тижневий звіт у HTML: /api/report/weekly.html + HTML-формат email."""
import pytest
from email import message_from_bytes

from app import config, report_html, report_pdf


def test_build_html_is_selfcontained_and_escapes():
    report = {
        "days": 7,
        "rooms": {
            "Вітальня": {"avg": 21.5, "min": 19.0, "max": 24.0, "humidity_avg": 42.0, "samples": 168},
            "<script>x</script>": {"avg": 20.0, "min": 18.0, "max": 22.0, "samples": 10},
        },
    }
    out = report_html.build_html(report)
    assert out.startswith("<!DOCTYPE html>")
    assert "Вітальня" in out
    assert "&lt;script&gt;" in out and "<script>" not in out
    assert "<style>" in out and "src=" not in out  # стилі інлайн, зовнішніх ресурсів немає


def test_build_html_empty_report():
    out = report_html.build_html({"days": 7, "rooms": {}})
    assert "Немає даних" in out


def test_weekly_html_endpoint(client):
    r = client.get("/api/report/weekly.html")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "attachment" in r.headers["content-disposition"]
    assert "weekly-" in r.headers["content-disposition"] and ".html" in r.headers["content-disposition"]
    for room in config.DEFAULT_ROOMS:
        assert room in r.text


class FakeSMTP:
    last = None

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.tls, self.logged_in, self.sent = host, port, False, None, []
        FakeSMTP.last = self

    def starttls(self):
        self.tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_smtp(monkeypatch):
    monkeypatch.setattr(report_pdf.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def test_send_html_email_sends_html_part(fake_smtp):
    cfg = {"host": "smtp.example.com", "port": 587, "from": "cc@example.com"}
    report_pdf.send_html_email(cfg, "you@example.com", "<h1>звіт</h1>")
    smtp = fake_smtp.last
    assert len(smtp.sent) == 1
    parsed = message_from_bytes(smtp.sent[0].as_bytes())
    html_parts = [p for p in parsed.walk() if p.get_content_type() == "text/html"]
    assert len(html_parts) == 1
    assert "звіт" in html_parts[0].get_payload()


def test_email_endpoint_html_format(client, fake_smtp):
    r = client.post("/api/report/email", json={
        "to": "you@example.com", "format": "html",
        "smtp_host": "smtp.example.com", "smtp_port": 587, "smtp_from": "cc@example.com",
    })
    assert r.status_code == 200
    assert r.json()["format"] == "html"
    parsed = message_from_bytes(fake_smtp.last.sent[0].as_bytes())
    assert any(p.get_content_type() == "text/html" for p in parsed.walk())


def test_email_endpoint_rejects_unknown_format(client):
    r = client.post("/api/report/email", json={"to": "you@example.com", "format": "docx"})
    assert r.status_code == 422
    assert "format" in r.json()["detail"]
