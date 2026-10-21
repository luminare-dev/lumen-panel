"""Lumen Dark covers every light surface of the default theme's standard stylesheet (read-only).

Lumen Dark draws on top of the default theme's light stylesheet (style.css). This test reads that
stylesheet from the KeyHelp install on this machine, finds every rule that paints a light
background, a light inset shadow (the panel's autofill colour), light borders, dark text, or a
dark mark on a pseudo-element (spinners, arrows), and checks that Lumen's stylesheets (the
components, the Lumen Dark additions in src/styles/night/ and rtl.css) override the same selector
and property, with !important where the base uses it. A second test does the same for the editor
stylesheets the panel loads after Lumen's (CodeMirror, Trumbowyg), whose overrides must carry the
.lumen-night prefix. The few rules that need no override are listed below with the reason. Nothing
of the default stylesheets is copied: only their selectors are compared at test time.

CI has no KeyHelp, so the tests are skipped there. On the server, they fail when a panel update
adds a light rule Lumen Dark does not cover yet.
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
VENDOR = KEYHELP / "theme" / "bulma" / "assets" / "vendor"
# The editor stylesheets the 26.1.1 templates load (in the page's CSS block, after Lumen's).
VENDOR_CSS = ("codemirror/codemirror.min.css", "codemirror/addon/dialog/dialog.css",
              "codemirror/addon/scroll/simplescrollbars.css", "codemirror/addon/search/matchesonscrollbar.css",
              "codemirror/addon/display/fullscreen.css", "trumbowyg/ui/trumbowyg.min.css",
              "trumbowyg/plugins/colors/ui/trumbowyg.colors.min.css")

# Bulma parts and colour variants the panel's templates and scripts do not use (checked against
# KeyHelp 26.1.1: no template or panel script writes these classes).
UNUSED = re.compile(
    r"\.is-white\b|\.is-light\b|\.is-black\b|\.is-inverted\b|\.hero\b|\.navbar|\.panel|\.media\b"
    r"|\.select2-container--classic|\.has-text-white|\.table t[dh]\.is-|\.file\.is-"
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
}
# Base rules Lumen covers with a more specific selector (the dropdown sits in
# .select2-container--default, every meter is a progress.progress): the test checks the rule named
# here instead, with !important where the base uses it.
MORE_SPECIFIC = {
    ".select2-search--dropdown": ".select2-container--default .select2-search--dropdown",
    ".select2-search--dropdown .select2-search__field":
        ".select2-container--default .select2-search--dropdown .select2-search__field",
    ".select2-results__options": ".select2-container--default .select2-results__options",
    ".select2-results__option:not(:last-child)": ".select2-container--default .select2-results__option:not(:last-child)",
    ".select2-selection__rendered": ".select2-container--default .select2-selection__rendered",
    "progress[data-load-level=medium]::-webkit-progress-value": ".progress[data-load-level=medium]::-webkit-progress-value",
    "progress[data-load-level=medium]::-moz-progress-bar": ".progress[data-load-level=medium]::-moz-progress-bar",
}
# Editor rules that need no override in Lumen Dark, by reason.
VENDOR_NOT_NEEDED = re.compile(
    # The panel wraps the editor in .trumbowyg-dark only when it reports its own dark mode, which it
    # never does for Lumen Dark (has_dark_mode false).
    r"\.trumbowyg-dark\b"
    # Options and add-ons the panel does not use (no resetCss option, no rulers add-on).
    r"|\.trumbowyg-reset-css\b|\.CodeMirror-ruler\b"
    # The white ring around the hovered or focused swatch of the colour menus: a mark on the swatch,
    # visible on the dark menu as well.
    r"|\.trumbowyg-dropdown-(?:back|fore)Color\b.*::after$")


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
    # Firefox reads the unprefixed ::selection (since Firefox 62), which Lumen's rules use.
    s = s.replace("::-moz-selection", "::selection")
    return re.sub(r"(?<!:):(before|after)", r"::\1", s)


COLOUR_RE = re.compile(r"#[0-9a-f]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|(?<![-\w])white(?![-\w])")


def colour(token: str) -> tuple[int, int, int] | None:
    """One CSS colour as RGB; None for a transparent one or one that cannot be read."""
    v = token.strip().lower()
    if m := re.fullmatch(r"#([0-9a-f]{3,8})", v):
        h = m.group(1)
        h = "".join(c * 2 for c in h[:3]) if len(h) in (3, 4) else h[:6]
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if m := re.match(r"rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:[ ,/]+([\d.]+%?))?", v):
        alpha = m.group(4)
        if alpha is not None and float(alpha.rstrip("%")) == 0:
            return None
        return int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
    if m := re.match(r"hsla?\(\s*([\d.]+)(?:deg)?[ ,]+([\d.]+)%[ ,]+([\d.]+)%(?:[ ,/]+([\d.]+%?))?", v):
        alpha = m.group(4)
        if alpha is not None and float(alpha.rstrip("%")) == 0:
            return None
        r, g, b = colorsys.hls_to_rgb(float(m.group(1)) / 360, float(m.group(3)) / 100, float(m.group(2)) / 100)
        return round(r * 255), round(g * 255), round(b * 255)
    if v == "white":
        return 255, 255, 255
    return None


def rgb(value: str) -> tuple[int, int, int] | None:
    """The first colour of a value that is not transparent."""
    for m in COLOUR_RE.finditer(value.lower()):
        if (c := colour(m.group(0))) is not None:
            return c
    return None


def luminance(c: tuple[int, int, int]) -> float:
    def ch(x: int) -> float:
        x = x / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


# A dark mark drawn with borders on a pseudo-element (a spinner, an arrow) needs 3:1 on the card
# (#10182B): every colour darker than this luminance falls below that.
DARK_MARK = 0.13


def group_of(prop: str) -> str | None:
    """The property group an override has to set: what replaces what."""
    if prop in ("background", "background-color"):
        return "background"
    if prop in ("box-shadow", "-webkit-box-shadow"):
        return "shadow"
    if prop.startswith("border"):
        return "border"
    if prop in ("color", "-webkit-text-fill-color"):
        return prop
    return None


def light_rules(css: str) -> list[tuple[str, str, str, bool]]:
    """(selector, property group, value, !important) of every light background or inset shadow,
    light border, dark text, or dark mark on a ::before or ::after."""
    found = []
    for selectors, body in rules(css):
        for decl in body.split(";"):
            prop, _, value = decl.partition(":")
            prop = prop.strip().lower()
            c = rgb(value) if value else None
            if c is None or group_of(prop) is None:
                continue
            light = luminance(c)
            important = "!important" in value.replace(" ", "")
            is_border = prop.startswith("border") and ("color" in prop or prop.count("-") <= 1)
            # The colour of an inset shadow layer (a fill, like the panel's autofill colour).
            fills = [rgb(layer) for layer in re.split(r",(?![^(]*\))", value) if "inset" in layer]
            fill_light = max((luminance(f) for f in fills if f is not None), default=0.0)
            for sel in (norm(x) for x in selectors.split(",")):
                if prop in ("background", "background-color") and light > 0.45:
                    group = "background"
                elif group_of(prop) == "shadow" and fill_light > 0.45:
                    group = "shadow"
                elif prop in ("color", "-webkit-text-fill-color") and light < 0.2:
                    group = prop
                elif is_border and light > 0.5:
                    group = "border"
                elif is_border and light < DARK_MARK and sel.endswith(("::before", "::after")):
                    group = "border"
                else:
                    continue
                found.append((sel, group, value.strip(), important))
    return found


def overrides(paths: list[Path], prefix: str = "") -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """The property groups our rules set per selector, and those they set with !important. With
    ``prefix``, only selectors that start with it count (and are recorded without it)."""
    groups: dict[str, set[str]] = {}
    important: dict[str, set[str]] = {}
    for path in paths:
        for selectors, body in rules(path.read_text(encoding="utf-8")):
            decls = [d.partition(":") for d in body.split(";") if ":" in d]
            for s in selectors.split(","):
                sel = norm(s)
                if prefix:
                    if not sel.startswith(prefix):
                        continue
                    sel = sel[len(prefix):]
                else:
                    sel = re.sub(r"^\.lumen-night ", "", sel)
                for prop, _, value in decls:
                    group = group_of(prop.strip().lower())
                    if group is None:
                        continue
                    groups.setdefault(sel, set()).add(group)
                    if "!important" in value.replace(" ", ""):
                        important.setdefault(sel, set()).add(group)
    return groups, important


def lumen_overrides() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    files = sorted((STYLES / "components").glob("*.css")) + sorted((STYLES / "night").glob("*.css"))
    return overrides(files + [STYLES / "rtl.css"])


def uncovered(found: list[tuple[str, str, str, bool]], ours: tuple[dict[str, set[str]], dict[str, set[str]]],
              skip, more_specific: dict[str, str] | None = None) -> list[str]:
    groups, important = ours
    missing = set()
    for base_sel, group, value, imp in found:
        if skip(base_sel):
            continue
        sel = (more_specific or {}).get(base_sel, base_sel)
        if group not in groups.get(sel, set()):
            missing.add(f"{sel} ({group}: {value})")
        elif imp and group not in important.get(sel, set()):
            missing.add(f"{sel} ({group}: {value}; the base uses !important, so must the override)")
    return sorted(missing)


class AuditTest(unittest.TestCase):
    def test_the_audit_finds_what_it_should(self):
        css = (".a{background-color:#fff}.b{color:hsl(0,0%,21%)}.c{border:1px solid #dbdbdb}.d{color:#fff}"
               ".e:focus{-webkit-box-shadow:0 0 0 .125em hsla(217,71%,53%,.25),0 0 0 100px #e8f0fe inset}"
               ".f{box-shadow:0 0 0 1px #fff}"
               ".g::after{border-color:rgba(0,0,0,0) rgba(0,0,0,0) hsl(0,0%,21%) hsl(0,0%,21%) !important}"
               ".h{border-color:hsl(0,0%,21%)}.i{background-color:#fef2d1 !important}")
        self.assertEqual([(s, g, i) for s, g, _, i in light_rules(css)],
                         [(".a", "background", False), (".b", "color", False), (".c", "border", False),
                          (".e:focus", "shadow", False), (".g::after", "border", True), (".i", "background", True)])
        self.assertEqual(norm('.t[data-theme~="light-border"]>.x:after'), ".t[data-theme~=light-border] > .x::after")
        self.assertEqual(norm(".x::-moz-selection"), ".x::selection")

    def test_an_override_without_important_does_not_count_against_important(self):
        found = light_rules(".s{background-color:#fef2d1 !important}.t{background-color:#fff}")
        ours = ({".s": {"background"}, ".t": {"background"}}, {})
        self.assertEqual(uncovered(found, ours, lambda _s: False),
                         [".s (background: #fef2d1 !important; the base uses !important, so must the override)"])
        self.assertEqual(uncovered(found, (ours[0], {".s": {"background"}}), lambda _s: False), [])


@unittest.skipUnless(BASE_CSS.is_file(), "no KeyHelp install on this machine")
class NightCoverageTest(unittest.TestCase):
    def test_every_light_rule_of_the_base_has_a_dark_override(self):
        found = light_rules(BASE_CSS.read_text(encoding="utf-8-sig"))
        self.assertGreater(len(found), 200, "the default stylesheet was read")
        missing = uncovered(found, lumen_overrides(), lambda sel: sel in NOT_NEEDED or bool(UNUSED.search(sel)),
                            MORE_SPECIFIC)
        self.assertEqual(missing, [], "add a rule to src/styles/night/ (or a reviewed entry above)")

    def test_every_light_rule_of_the_editors_has_a_dark_override(self):
        """The editors' stylesheets load after Lumen's: each light rule needs the same selector with
        the .lumen-night prefix in night/editors.css, which outranks it."""
        ours = overrides([STYLES / "night" / "editors.css"], prefix=".lumen-night ")
        missing: list[str] = []
        for rel in VENDOR_CSS:
            path = VENDOR / rel
            self.assertTrue(path.is_file(), f"{rel}: not found; update VENDOR_CSS for this panel version")
            found = light_rules(path.read_text(encoding="utf-8-sig"))
            missing += [f"{rel}: {m}" for m in uncovered(found, ours, lambda sel: bool(VENDOR_NOT_NEEDED.search(sel)))]
        self.assertEqual(missing, [], "add a .lumen-night rule to src/styles/night/editors.css (or a reviewed entry)")


if __name__ == "__main__":
    unittest.main()
