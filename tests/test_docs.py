"""Documentation that must follow the code: every command-line option is documented."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))

from lumen_panel.cli import parser  # noqa: E402


def options() -> set[str]:
    found: set[str] = set()
    p = parser()
    for action in p._subparsers._group_actions:  # noqa: SLF001 (argparse has no public API for this)
        for sub in action.choices.values():
            for a in sub._actions:  # noqa: SLF001
                found.update(o for o in a.option_strings if o.startswith("--") and o != "--help")
    return found


class ConfigurationDocTest(unittest.TestCase):
    def test_every_option_is_in_configuration_md(self):
        doc = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
        documented = set(re.findall(r"^\| `(--[a-z-]+)`", doc, re.MULTILINE))
        self.assertEqual(options() - documented, set(), "add the option to docs/configuration.md")
        self.assertEqual(documented - options(), set(), "remove the stale option from docs/configuration.md")

    def test_exit_codes_match(self):
        from lumen_panel import install as inst

        doc = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
        for code in (inst.EXIT_OK, inst.EXIT_FAILED, inst.EXIT_USAGE, inst.EXIT_NOT_INSTALLED, inst.EXIT_ACTIVE,
                     inst.EXIT_UNCONFIRMED, inst.EXIT_REBUILD_NEEDED):
            self.assertRegex(doc, re.compile(rf"^\| {code} \|", re.MULTILINE), f"exit code {code} is not documented")


if __name__ == "__main__":
    unittest.main()
