"""Lumen Dark covers every light surface of the default theme's standard stylesheet (read-only).

Lumen Dark draws on top of the default theme's light stylesheet (style.css). This test reads that
stylesheet from the KeyHelp install on this machine, finds every rule that paints a light
background, light borders or dark text, and checks that Lumen's stylesheets (the components, the
Lumen Dark additions in src/styles/night/ and rtl.css) override the same selector and property.
The few rules that need no override are listed below with the reason. Nothing of the default
stylesheet is copied: only its selectors are compared at test time.

CI has no KeyHelp, so the test is skipped there. On the server, it fails when a panel update adds
a light rule Lumen Dark does not cover yet.
"""

from __future__ import annotations

import colorsys
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLES = ROOT / "src" / "styles"
KEYHELP = Path(os.environ.get("LUMEN_KEYHELP_ROOT", "/home/keyhelp/www/keyhelp"))
BASE_CSS = KEYHELP / "theme" / "bulma" / "assets" / "css" / "style.css"

# Bulma parts and colour variants the panel's templates and scripts do not use (checked against
# KeyHelp 26.1.1: no template or panel script writes these classes).
UNUSED = re.compile(
    r"\.is-white\b|\.is-light\b|\.is-black\b|\.is-inverted\b|\.hero\b|\.navbar|\.panel|\.media\b"
    r"|\.select2-container--classic|\.has-text-white|\.table t[dh]\.is-|\.progress\.is-|\.file\.is-"
    r"|\.has-background-warning|\.fa-border"
    r"|::-ms-|:-ms-|::-moz-placeholder|:-moz-placeholder|::-webkit-input-placeholder")
# Rules that need no override, by reason.
NOT_NEEDED = {
    # The white cross of close buttons stays white on Lumen's grey disc (docs/contrast.md, 4.71:1).
    ".modal-close::before", ".modal-close::after", ".delete::before", ".delete::after",
    # Invisible (opacity 0) or never matching (a container nested in a container).
    ".select2-close-mask",
    ".select2-container--default .select2-container--default.select2-container--disabled .select2-selection--single",
    ".select2-container--default .select2-container--default.select2-container--disabled .select2-selection--multiple",
    ".select fieldset[disabled] select",
    # Covered by the !important rules for input[disabled] and textarea[disabled] (same elements).
    "[disabled].input", "[disabled].textarea",
    # Covered by Lumen with a more specific selector (the dropdown sits in .select2-container--default,
    # every meter is a progress.progress).
    ".select2-search--dropdown", ".select2-search--dropdown .select2-search__field", ".select2-results__options",
    ".select2-results__option:not(:last-child)", ".select2-results__option--selected", ".select2-selection__rendered",
    "progress[data-load-level=medium]::-webkit-progress-value", "progress[data-load-level=medium]::-moz-progress-bar",
}


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def rules(css: str) -> list[tuple[str, str]]:
    """(selector list, declarations) of every style rule, @media blocks included."""
    css = strip_comments(css)
    out: list[tuple[str, str]] = []
    depth_stack: list[str] = []
    buf, i = "", 0
    while i < len(css):
        ch = css[i]
        if ch == "{":
            head, buf = buf.strip(), ""
            if head.startswith(("@media", "@supports")):
                depth_stack.append(head)
                i += 1
                continue
            if head.startswith("@"):
                depth, i = 1, i + 1
                while depth and i < len(css):
                    depth += {"{": 1, "}": -1}.get(css[i], 0)
                    i += 1
                continue
            end = css.index("}", i)
            out.append((head, css[i + 1:end]))
            i = end + 1
            continue
        if ch == "}":
            if depth_stack:
                depth_stack.pop()
            buf, i = "", i + 1
            continue
        buf += ch
        i += 1
    return out


def norm(selector: str) -> str:
    s = re.sub(r"\s*(?<![~|^$*])([>~+])(?!=)\s*", r" \1 ", selector.strip())
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\[([\w-]+)([~^$*|]?=)\"?([^\]\"]*)\"?\]", r"[\1\2\3]", s)
    return re.sub(r"(?<!:):(before|after)", r"::\1", s)


def rgb(value: str) -> tuple[int, int, int] | None:
    v = value.strip().lower()
    if m := re.search(r"#([0-9a-f]{3,8})\b", v):
        h = m.group(1)
        h = "".join(c * 2 for c in h[:3]) if len(h) in (3, 4) else h[:6]
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if m := re.search(r"rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:[ ,/]+([\d.]+))?", v):
        if m.group(4) is not None and float(m.group(4)) == 0:
            return None
        return int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
    if m := re.search(r"hsla?\(\s*([\d.]+)(?:deg)?[ ,]+([\d.]+)%[ ,]+([\d.]+)%", v):
        r, g, b = colorsys.hls_to_rgb(float(m.group(1)) / 360, float(m.group(3)) / 100, float(m.group(2)) / 100)
        return round(r * 255), round(g * 255), round(b * 255)
    if re.search(r"(?<![-\w])white(?![-\w])", v):
        return 255, 255, 255
    return None


def luminance(c: tuple[int, int, int]) -> float:
    def ch(x: int) -> float:
        x = x / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def light_rules(css: str) -> list[tuple[str, str, str]]:
    """(selector, property group, value) of every light background, light border or dark text."""
    found = []
    for selectors, body in rules(css):
        for decl in body.split(";"):
            prop, _, value = decl.partition(":")
            prop = prop.strip().lower()
            colour = rgb(value) if value else None
            if colour is None:
                continue
            light = luminance(colour)
            if prop in ("background", "background-color") and light > 0.45:
                group = "background"
            elif prop == "color" and light < 0.2:
                group = "color"
            elif prop.startswith("border") and ("color" in prop or prop.count("-") <= 1) and light > 0.5:
                group = "border"
            else:
                continue
            found += [(norm(s), group, value.strip()) for s in selectors.split(",")]
    return found


def lumen_overrides() -> dict[str, set[str]]:
    files = sorted((STYLES / "components").glob("*.css")) + sorted((STYLES / "night").glob("*.css"))
    out: dict[str, set[str]] = {}
    for path in files + [STYLES / "rtl.css"]:
        for selectors, body in rules(path.read_text(encoding="utf-8")):
            props = {d.partition(":")[0].strip().lower() for d in body.split(";") if ":" in d}
            groups = {"background" if p in ("background", "background-color") else
                      "border" if p.startswith("border") else p for p in props}
            for s in selectors.split(","):
                out.setdefault(re.sub(r"^\.lumen-night ", "", norm(s)), set()).update(groups)
    return out


@unittest.skipUnless(BASE_CSS.is_file(), "no KeyHelp install on this machine")
class NightCoverageTest(unittest.TestCase):
    def test_every_light_rule_of_the_base_has_a_dark_override(self):
        ours = lumen_overrides()
        found = light_rules(BASE_CSS.read_text(encoding="utf-8-sig"))
        self.assertGreater(len(found), 200, "the default stylesheet was read")
        missing = sorted({f"{sel} ({group}: {value})" for sel, group, value in found
                          if group not in ours.get(sel, set()) and sel not in NOT_NEEDED and not UNUSED.search(sel)})
        self.assertEqual(missing, [], "add a rule to src/styles/night/ (or a reviewed entry above)")

    def test_the_audit_finds_what_it_should(self):
        css = ".a{background-color:#fff}.b{color:hsl(0,0%,21%)}.c{border:1px solid #dbdbdb}.d{color:#fff}"
        self.assertEqual([(s, g) for s, g, _ in light_rules(css)], [(".a", "background"), (".b", "color"),
                                                                     (".c", "border")])
        self.assertEqual(norm('.t[data-theme~="light-border"]>.x:after'), ".t[data-theme~=light-border] > .x::after")


if __name__ == "__main__":
    unittest.main()
