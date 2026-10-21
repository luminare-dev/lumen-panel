"""The patch set against the KeyHelp install on this machine, when there is one (read-only).

CI has no KeyHelp, so this test is skipped there; on the server it proves that every anchor occurs
exactly once in the installed default theme before anything is built.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))

from lumen_panel.patches import load_patches  # noqa: E402

KEYHELP = Path(os.environ.get("LUMEN_KEYHELP_ROOT", "/home/keyhelp/www/keyhelp"))
TEMPLATES = KEYHELP / "theme" / "bulma" / "templates"


@unittest.skipUnless((TEMPLATES / "layout" / "base.twig").is_file(), "no KeyHelp install on this machine")
class LiveAnchorTest(unittest.TestCase):
    def test_every_anchor_occurs_exactly_once(self):
        contents: dict[str, str] = {}
        for patch in load_patches(ROOT / "patches"):
            text = contents.setdefault(patch.file, (TEMPLATES / patch.file).read_text(encoding="utf-8"))
            self.assertEqual(text.count(patch.anchor), 1, f"{patch.source}: {patch.id} in {patch.file}")


if __name__ == "__main__":
    unittest.main()
