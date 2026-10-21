"""Checks on the stylesheets: tokens, contrast table, right-to-left safety, cascade order."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLES = ROOT / "src" / "styles"
CSS_FILES = sorted(STYLES.rglob("*.css")) + [ROOT / "island" / "src" / "palette.css"]
# The Luminare brand kit is not part of the repository; point LUMEN_BRAND_KIT at a local copy to
# compare the brand colours with it.
KIT = Path(os.environ.get("LUMEN_BRAND_KIT", "/nonexistent"))

sys.path.insert(0, str(ROOT / "scripts"))
import contrast  # noqa: E402


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


class TokenTest(unittest.TestCase):
    def test_every_used_token_is_defined(self):
        tokens = (STYLES / "tokens.css").read_text(encoding="utf-8")
        defined = set(re.findall(r"--lm-([a-z0-9-]+)\s*:", tokens))
        for path in CSS_FILES:
            used = set(re.findall(r"var\(--lm-([a-z0-9-]+)", path.read_text(encoding="utf-8")))
            self.assertEqual(used - defined, set(), f"{path.relative_to(ROOT)} uses undefined tokens")

    def test_dark_block_overrides_only_known_tokens(self):
        light, dark = contrast.blocks((STYLES / "tokens.css").read_text(encoding="utf-8"))
        self.assertLessEqual(set(contrast.declarations(dark)), set(contrast.declarations(light)))

    def test_contrast_table_is_current_and_passes(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "contrast.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    @unittest.skipUnless((KIT / "palette" / "tokens.json").is_file(), "brand kit not available here")
    def test_brand_colours_match_the_kit(self):
        css = (STYLES / "tokens.css").read_text(encoding="utf-8")
        self.assertEqual(contrast.kit_problems(css, KIT), [])

    def test_ratio_formula(self):
        self.assertAlmostEqual(contrast.ratio("#000000", "#FFFFFF"), 21.0, places=2)
        self.assertAlmostEqual(contrast.ratio("#0A1224", "#FFFFFF"), 18.66, places=1)
        self.assertEqual(contrast.mix("#000000", "#FFFFFF", 0.5), "#808080")


class SyntaxTest(unittest.TestCase):
    def test_braces_balance_and_declarations_are_complete(self):
        """A cheap guard for CI jobs without the CSS build: the bundler would reject these too."""
        for path in CSS_FILES:
            css = strip_comments(path.read_text(encoding="utf-8"))
            depth = 0
            for ch in css:
                depth += {"{": 1, "}": -1}.get(ch, 0)
                self.assertGreaterEqual(depth, 0, f"{path.name}: '}}' without '{{'")
            self.assertEqual(depth, 0, f"{path.name}: unbalanced braces")
            for block in re.findall(r"\{([^{}]*)\}", css):
                for decl in filter(None, (d.strip() for d in block.split(";"))):
                    self.assertRegex(decl, r"^-?-?[a-z][-a-z0-9]*\s*:\s*\S", f"{path.name}: {decl!r}")


class RtlAndCascadeTest(unittest.TestCase):
    PHYSICAL = re.compile(r"(?<![-\w])(margin|padding)-(left|right)\s*:\s*([^;]+);"
                          r"|(?<![-\w])(left|right)\s*:\s*([^;]+);"
                          r"|(?<![-\w])border-(left|right)(?:-width)?\s*:\s*([^;]+);"
                          r"|text-align\s*:\s*(left|right)")

    def test_no_physical_offsets_except_resets(self):
        """Only logical properties set space or position; a physical side may only be reset to 0."""
        for path in CSS_FILES:
            if path.name == "rtl.css":
                continue
            for m in self.PHYSICAL.finditer(strip_comments(path.read_text(encoding="utf-8"))):
                value = next(v for v in (m.group(3), m.group(5), m.group(7)) if v is not None) if not m.group(8) else m.group(8)
                self.assertIn(value.strip(), ("0", "0px"), f"{path.relative_to(ROOT)}: {m.group(0)!r}")

    def test_no_cascade_layers(self):
        """Layered rules lose to the default theme's unlayered rules, so no @layer is used."""
        for path in CSS_FILES:
            self.assertNotIn("@layer", strip_comments(path.read_text(encoding="utf-8")), path.name)

    def test_reduced_motion_is_respected(self):
        motion = (STYLES / "components" / "motion.css").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: reduce", motion)
        palette = (ROOT / "island" / "src" / "palette.css").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: no-preference", palette)

    def test_index_imports_every_component(self):
        index = (STYLES / "index.css").read_text(encoding="utf-8")
        for path in sorted((STYLES / "components").glob("*.css")):
            self.assertIn(f'@import "components/{path.name}";', index)
        self.assertNotIn("night", index, "Lumen's own stylesheets never include the Lumen Dark additions")


class NightTest(unittest.TestCase):
    """Lumen Dark: lumen-night.css = index.css + the dark tokens on :root + night.css."""

    def test_night_imports_every_part(self):
        night = (STYLES / "night.css").read_text(encoding="utf-8")
        parts = sorted((STYLES / "night").glob("*.css"))
        self.assertGreaterEqual(len(parts), 5)
        for path in parts:
            self.assertIn(f'@import "night/{path.name}";', night)

    def test_the_build_writes_both_night_stylesheets(self):
        script = (ROOT / "scripts" / "build-css.mjs").read_text(encoding="utf-8")
        self.assertIn('bundled("night.css")', script)
        self.assertRegex(script, r'"lumen-night\.css": base \+ nightTokens \+ night,')
        self.assertRegex(script, r'"lumen-night-rtl\.css": base \+ nightTokens \+ night \+ rtl,')
        self.assertRegex(script, r'"lumen-dark\.css": base \+ dark,', "Lumen's builds stay as they were")

    def test_the_dark_tokens_make_the_page_dark(self):
        _, dark = contrast.blocks((STYLES / "tokens.css").read_text(encoding="utf-8"))
        self.assertIn("color-scheme: dark;", dark, "native controls and scrollbars render dark")
        decls = contrast.mode_declarations((STYLES / "tokens.css").read_text(encoding="utf-8"))
        self.assertEqual(contrast.resolve("bg", decls["night"]), "#0A1224", "the Night background")
        self.assertEqual(decls["night"], decls["dark"])

    def test_editor_rules_win_over_the_editor_stylesheets(self):
        """CodeMirror's and Trumbowyg's stylesheets load after Lumen's, so each editor rule needs the
        .lumen-night prefix to outrank them."""
        css = strip_comments((STYLES / "night" / "editors.css").read_text(encoding="utf-8"))
        selectors = [sel.strip() for block in re.findall(r"([^{}]+)\{", css) for sel in block.split(",")]
        self.assertGreater(len(selectors), 40)
        for sel in selectors:
            self.assertTrue(sel.startswith(".lumen-night "), sel)

    def test_night_rules_other_than_the_editors_keep_white_label_in_charge(self):
        """Outside the editors, rules match the selector they replace (no .lumen-night prefix), so
        White Label CSS, which loads later, can still override them."""
        for path in sorted((STYLES / "night").glob("*.css")):
            if path.name == "editors.css":
                continue
            self.assertNotIn(".lumen-night", strip_comments(path.read_text(encoding="utf-8")), path.name)

    def test_every_pair_is_checked_for_lumen_dark(self):
        pairs = json.loads((STYLES / "contrast-pairs.json").read_text(encoding="utf-8"))["pairs"]
        rows, problems = contrast.analyse((STYLES / "tokens.css").read_text(encoding="utf-8"), pairs)
        self.assertEqual(problems, [])
        for row in rows:
            self.assertIsNotNone(row["night"], row["pair"])
        night_only = [row for row in rows if row["pair"].get("modes") == ["night"]]
        self.assertGreaterEqual(len(night_only), 5)
        doc = (ROOT / "docs" / "contrast.md").read_text(encoding="utf-8")
        self.assertIn("## Lumen Dark only", doc)
        self.assertIn("Dark and Lumen Dark", doc)


if __name__ == "__main__":
    unittest.main()
