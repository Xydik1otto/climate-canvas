"""OSS hygiene: community files exist, no privacy leaks in tracked files."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE_EXT = {".png", ".ico", ".db", ".pyc"}


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
    return [ROOT / f for f in out.splitlines() if f]


def test_community_files_exist():
    for rel in ("CONTRIBUTING.md", "SECURITY.md",
                ".github/ISSUE_TEMPLATE/bug_report.md",
                ".github/ISSUE_TEMPLATE/feature_request.md"):
        assert (ROOT / rel).is_file(), f"missing {rel}"


def test_community_files_are_bilingual_and_not_russian():
    for rel in ("CONTRIBUTING.md", "SECURITY.md",
                ".github/ISSUE_TEMPLATE/bug_report.md",
                ".github/ISSUE_TEMPLATE/feature_request.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "English" in text or "🇬🇧" in text, f"{rel}: no English section"
        assert "Україн" in text or "🇺🇦" in text, f"{rel}: no Ukrainian section"
        for char in "ыэъЫЭЪ":
            assert char not in text, f"Russian letter {char!r} in {rel}"


def test_security_doc_warns_about_token_in_git():
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "HASS_TOKEN" in text
    assert "git" in text.lower()


def test_gitignore_covers_secrets_and_local_data():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gi
    assert "*.db" in gi
    assert "data/" in gi  # settings.json with the HA token lives here
    assert "*.egg-info/" in gi


def test_no_settings_with_token_is_tracked():
    for f in tracked_files():
        assert "data/settings.json" not in str(f), "token config must never be tracked"


def test_no_private_paths_in_tracked_files():
    """No developer-machine absolute paths (G:\\, C:\\Users) may leak into the repo."""
    for f in tracked_files():
        if f.suffix.lower() in IGNORE_EXT or not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for marker in ("G:\\", "C:\\Users", "/c/Users"):
            assert marker not in text, f"private path marker {marker!r} found in {f.name}"


# These test files intentionally contain the Russian-only letters as scan literals.
_RU_SCAN_SELF = {"test_oss_hygiene.py", "test_i18n.py", "test_readmes.py", "test_install_doc.py"}


def test_no_russian_in_tracked_text_files():
    for f in tracked_files():
        if f.suffix.lower() in IGNORE_EXT or not f.is_file():
            continue
        if f.name in _RU_SCAN_SELF:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for char in "ыэъЫЭЪ":
            assert char not in text, f"Russian letter {char!r} in {f.name}"


def test_no_hardcoded_tokens_in_tracked_files():
    """The real token must come from env or the UI wizard, never be committed."""
    import re
    for f in tracked_files():
        if f.suffix not in (".py", ".js", ".html", ".json", ".toml", ".cfg", ".ini") or not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # long opaque secrets assigned to token-ish variables
        for m in re.finditer(r"(token|password|secret)\s*[=:]\s*[\"']([A-Za-z0-9_\-]{20,})[\"']", text, re.IGNORECASE):
            value = m.group(2)
            assert value in ("your_long_lived_token",), \
                f"suspicious hardcoded secret in {f.name}: {m.group(0)[:60]}…"


def test_default_coordinates_are_the_public_default():
    from app import config

    # Kyiv as a city-level default is intentional and public; no real home address
    assert 50.0 < config.LATITUDE < 50.6
    assert 30.0 < config.LONGITUDE < 31.0
