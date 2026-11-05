"""Accessibility checks: every interactive element has an accessible name,
focus is visible via CSS, and both themes meet WCAG AA contrast (4.5:1)."""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
PAGES = ["index.html", "settings.html", "report.html"]


def html_of(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_all_buttons_have_accessible_names():
    for name in PAGES:
        html = html_of(name)
        for m in re.finditer(r"<button\b([^>]*)>(.*?)</button>", html, re.DOTALL):
            attrs, inner = m.group(1), m.group(2)
            label = re.search(r'aria-label="([^"]+)"', attrs)
            text = re.sub(r"<[^>]+>", "", inner).strip()
            assert label or text, f"{name}: button without accessible name: {attrs}"


def test_all_links_have_accessible_names():
    for name in PAGES:
        html = html_of(name)
        for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.DOTALL):
            attrs, inner = m.group(1), m.group(2)
            if "href" not in attrs:
                continue
            label = re.search(r'aria-label="([^"]+)"', attrs)
            text = re.sub(r"<[^>]+>", "", inner).strip()
            assert label or text, f"{name}: link without accessible name: {attrs}"


def test_inputs_have_label_or_aria_label():
    for name in PAGES:
        html = html_of(name)
        ids_with_label = set(re.findall(r'<label[^>]*for="([^"]+)"', html))
        for m in re.finditer(r"<input\b([^>]*)>", html):
            attrs = m.group(1)
            if 'type="hidden"' in attrs:
                continue
            input_id = re.search(r'id="([^"]+)"', attrs)
            has_aria = "aria-label" in attrs or "aria-labelledby" in attrs
            assert has_aria or (input_id and input_id.group(1) in ids_with_label), \
                f"{name}: input without a label: {attrs}"


def test_selects_have_aria_labels():
    for name in PAGES:
        html = html_of(name)
        for m in re.finditer(r"<select\b([^>]*)>", html):
            assert "aria-label" in m.group(1), f"{name}: select without aria-label: {m.group(1)}"


def test_canvas_charts_have_role_and_label():
    html = html_of("index.html")
    for m in re.finditer(r"<canvas\b([^>]*)>", html):
        attrs = m.group(1)
        assert 'role="img"' in attrs and "aria-label" in attrs, f"canvas missing role/aria-label: {attrs}"


def test_status_messages_are_aria_live():
    for name, status_id in (("index.html", None), ("settings.html", "setup-status"),
                            ("report.html", "email-status")):
        html = html_of(name)
        assert 'aria-live="polite"' in html, f"{name}: no aria-live status region"
        if status_id:
            m = re.search(rf'id="{status_id}"[^>]*', html)
            assert m and "aria-live" in m.group(0)


def test_focus_visible_styles_present():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert ":focus-visible" in css
    assert "outline" in css


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def chan(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg: str, bg: str) -> float:
    def rgb(hexcolor: str) -> tuple[float, float, float]:
        hexcolor = hexcolor.lstrip("#")
        return tuple(int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    l1, l2 = sorted((_relative_luminance(rgb(fg)), _relative_luminance(rgb(bg))), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def test_theme_contrast_meets_wcag_aa():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    dark = re.search(r":root \{(.*?)\}", css, re.DOTALL).group(1)
    light = re.search(r"body\.light \{(.*?)\}", css, re.DOTALL).group(1)
    fg_d = re.search(r"--fg:(#[0-9a-f]{6})", dark).group(1)
    bg_d = re.search(r"--bg:(#[0-9a-f]{6})", dark).group(1)
    fg_l = re.search(r"--fg:(#[0-9a-f]{6})", light).group(1)
    bg_l = re.search(r"--bg:(#[0-9a-f]{6})", light).group(1)
    assert _contrast(fg_d, bg_d) >= 4.5, f"dark theme contrast too low: {_contrast(fg_d, bg_d):.2f}"
    assert _contrast(fg_l, bg_l) >= 4.5, f"light theme contrast too low: {_contrast(fg_l, bg_l):.2f}"


def test_muted_text_still_readable():
    """Secondary text uses --muted: it must also clear AA on both backgrounds."""
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    dark = re.search(r":root \{(.*?)\}", css, re.DOTALL).group(1)
    muted = re.search(r"--muted:(#[0-9a-f]{6})", dark).group(1)
    bg = re.search(r"--bg:(#[0-9a-f]{6})", dark).group(1)
    assert _contrast(muted, bg) >= 4.5
