"""The patch sets against the KeyHelp install on this machine, when there is one (read-only).

CI has no KeyHelp, so these tests are skipped there; on the server they prove that every anchor of
both variants occurs exactly once in the installed default theme before anything is built, and
that Lumen Dark built from the real templates keeps the Pro boundary. The build goes to a
temporary folder; the KeyHelp install is only read.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))
sys.path.insert(0, str(ROOT / "tests"))

from lumen_panel.build import build  # noqa: E402
from lumen_panel.patches import load_patches  # noqa: E402
from lumen_panel.twig import asset_references  # noqa: E402
from lumen_panel.variants import LUMEN_DARK, VARIANTS  # noqa: E402
from lumen_panel.verify import verify  # noqa: E402

KEYHELP = Path(os.environ.get("LUMEN_KEYHELP_ROOT", "/home/keyhelp/www/keyhelp"))
TEMPLATES = KEYHELP / "theme" / "bulma" / "templates"


@unittest.skipUnless((TEMPLATES / "layout" / "base.twig").is_file(), "no KeyHelp install on this machine")
class LiveAnchorTest(unittest.TestCase):
    def test_every_anchor_occurs_exactly_once(self):
        contents: dict[str, str] = {}
        for variant in VARIANTS.values():
            for patch in load_patches(ROOT / "patches", variant.patch_overlay):
                text = contents.setdefault(patch.file, (TEMPLATES / patch.file).read_text(encoding="utf-8"))
                self.assertEqual(text.count(patch.anchor), 1,
                                 f"{variant.name}: {patch.source}: {patch.id} in {patch.file}")

    def test_lumen_dark_from_the_real_templates_keeps_the_pro_boundary(self):
        import fakekeyhelp as fk

        tmp = Path(tempfile.mkdtemp(prefix="lumen-live-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        assets = fk.make_assets(tmp / "assets")
        shot = tmp / "shot.png"
        shot.write_bytes(fk.tiny_png())
        out = build(KEYHELP, tmp / "lumen-dark", variant=LUMEN_DARK, assets_dir=assets, screenshot_fallback=shot).out_dir
        report = verify(out, KEYHELP)
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(any(p.startswith("pro boundary") for p in report.passed), report.passed)
        stylesheets: set[str] = set()
        for twig in (out / "templates").rglob("*.twig"):
            refs = asset_references(twig.read_text(encoding="utf-8", errors="replace"), "bulma")
            stylesheets.update(r for r in refs if r.startswith("assets/css/"))
        self.assertEqual(stylesheets, {"assets/css/style.css", "assets/css/style-rtl.css"},
                         "Lumen Dark loads only the default theme's standard stylesheets")


if __name__ == "__main__":
    unittest.main()
