"""Tests for UA/EN i18n: dictionaries complete, pages wired, no Russian."""
import json
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
PAGES = ["index.html", "settings.html", "report.html"]


def load_i18n_source() -> str:
    return (STATIC / "i18n.js").read_text(encoding="utf-8")


KEY_RE = r"(?:\{|\n\s*|,\s*)([a-z0-9_]+):\s*\"((?:[^\"\\]|\\.)*)\""


def extract_dict_keys(block: str) -> set[str]:
    return {m[0] for m in re.findall(KEY_RE, block)}


def uk_block() -> str:
    src = load_i18n_source()
    return re.search(r"uk: \{(.*?)\n    \},", src, re.DOTALL).group(1)


def en_block() -> str:
    src = load_i18n_source()
    return re.search(r"en: \{(.*?)\n    \},", src, re.DOTALL).group(1)


def test_both_dictionaries_have_identical_key_sets():
    uk, en = extract_dict_keys(uk_block()), extract_dict_keys(en_block())
    assert uk, "uk dictionary is empty"
    assert uk == en, f"missing in uk: {sorted(en - uk)}; missing in en: {sorted(uk - en)}"


def test_english_translations_are_not_left_ukrainian():
    en = en_block()
    # Ukrainian-specific letters that never occur in English strings
    for char in "іїєґІЇЄҐ":
        assert char not in en, f"Ukrainian letter {char!r} in the EN dictionary"


def test_no_russian_anywhere_in_static_files():
    # Russian-only Cyrillic letters (Ukrainian text never uses these)
    russian_only = "ыэъЫЭЪ"
    for path in STATIC.iterdir():
        if path.suffix in (".js", ".html", ".css", ".webmanifest", ".svg"):
            content = path.read_text(encoding="utf-8")
            for char in russian_only:
                assert char not in content, f"Russian letter {char!r} found in {path.name}"


def test_all_pages_include_i18n_script_and_lang_toggle():
    for name in PAGES:
        html = (STATIC / name).read_text(encoding="utf-8")
        assert 'src="/static/i18n.js"' in html, f"{name}: i18n.js not included"
        assert 'id="lang-toggle"' in html, f"{name}: language switcher missing"


def test_index_data_i18n_keys_exist_in_both_dicts():
    uk, en = extract_dict_keys(uk_block()), extract_dict_keys(en_block())
    for name in PAGES:
        html = (STATIC / name).read_text(encoding="utf-8")
        for key in re.findall(r'data-i18n(?:-title|-aria|-ph)?="([a-z0-9_]+)"', html):
            assert key in uk, f"{name}: data-i18n key {key!r} missing from uk dict"
            assert key in en, f"{name}: data-i18n key {key!r} missing from en dict"


def test_app_js_uses_i18n_for_dynamic_strings():
    src = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 't("card_humidity"' in src
    assert 't("energy_total"' in src
    assert "cc:langchange" in src  # re-renders on language switch
    # no hardcoded Ukrainian dynamic strings left
    assert "Точка роси:" not in src
    assert "Середня" not in src


def test_static_i18n_js_served_by_app(client):
    r = client.get("/static/i18n.js")
    assert r.status_code == 200
    assert "window.I18N" in r.text


def test_all_pages_served_with_lang_toggle(client):
    for path in ("/", "/settings", "/report"):
        r = client.get(path)
        assert r.status_code == 200
        assert 'id="lang-toggle"' in r.text


def test_en_dictionary_has_no_placeholder_params_mismatch():
    """Every {param} in en strings exists in the uk counterpart (same params)."""
    uk_src, en_src = uk_block(), en_block()
    uk_entries = dict(re.findall(KEY_RE, uk_src))
    en_entries = dict(re.findall(KEY_RE, en_src))
    for key, en_val in en_entries.items():
        params_en = set(re.findall(r"\{(\w+)\}", en_val))
        params_uk = set(re.findall(r"\{(\w+)\}", uk_entries.get(key, "")))
        assert params_en == params_uk, f"key {key}: params differ uk={params_uk} en={params_en}"


def test_lang_auto_detect_prefers_ukrainian_browsers():
    src = load_i18n_source()
    assert 'nav.startsWith("uk") ? "uk" : "en"' in src
    assert 'localStorage.setItem("cc-lang", lang)' in src  # choice is persisted
