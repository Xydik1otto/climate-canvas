"""Bilingual README checks: README.en.md exists, no Russian, links both ways."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_en_exists_and_links_back():
    en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "Українська версія" in en and "README.md" in en
    ua = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "English version" in ua and "README.en.md" in ua


def test_readme_en_no_russian():
    text = (ROOT / "README.en.md").read_text(encoding="utf-8")
    # Russian-only letters; Ukrainian words (like the cross-link) are fine
    for char in "ыэъЫЭЪ":
        assert char not in text, f"Russian letter {char!r} in English README"


def test_readme_en_covers_v1_features():
    text = (ROOT / "README.en.md").read_text(encoding="utf-8")
    for phrase in ("setup wizard", "humidity", "PDF", "SMTP", "demo", "export"):
        assert phrase in text


def test_readme_en_mentions_install_and_contributing():
    text = (ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "INSTALL.md" in text
    assert "CONTRIBUTING.md" in text
    assert "SECURITY.md" in text


def test_github_topics_documented():
    for name in ("README.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for topic in ("home-assistant", "smart-home", "visualization", "fastapi", "open-meteo"):
            assert topic in text, f"{name}: topic {topic} missing"


def test_version_badges_are_1_0_0():
    for name in ("README.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "version-1.0.0" in text, f"{name}: version badge not updated"
