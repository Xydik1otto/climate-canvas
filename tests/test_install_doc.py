"""INSTALL.md sanity: present, bilingual, no Russian, covers key steps."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_install_md_exists_and_bilingual():
    text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    assert "🇺🇦" in text and "🇬🇧" in text
    assert "shell:startup" in text  # Windows autostart
    assert "systemd" in text and "systemctl --user" in text  # Linux autostart
    assert "pip install -e ." in text
    # update instructions
    assert "git pull" in text


def test_install_md_has_no_russian():
    text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    for char in "ыэъЫЭЪ":
        assert char not in text


def test_install_md_referenced_from_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "INSTALL.md" in readme
