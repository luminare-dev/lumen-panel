"""Checks on the React parts and the shipped extras that need no Node.js: the command palette's
stylesheet fallbacks, the npm manifest, the optional systemd units, and that no KeyHelp file or
template line ever lands in the repository."""

from __future__ import annotations

import configparser
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "src" / "styles" / "tokens.css"
PALETTE_CSS = ROOT / "island" / "src" / "palette.css"
KEYHELP_THEME = Path("/home/keyhelp/www/keyhelp/theme/bulma")

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "generator"))
import contrast  # noqa: E402
from lumen_panel.cli import parser  # noqa: E402

FALLBACK_RE = re.compile(r"--p-[a-z0-9-]+:\s*var\(--lm-([a-z0-9-]+),\s*(#[0-9A-Fa-f]{6})\)")


def css_block(css: str, selector: str) -> str:
    start = css.index(selector + " {")
    return css[start:css.index("}", start)]


def token_values() -> tuple[dict[str, str], dict[str, str]]:
    light_block, dark_block = contrast.blocks(TOKENS.read_text(encoding="utf-8"))
    light = contrast.declarations(light_block)
    dark = {**light, **contrast.declarations(dark_block)}
    resolve = contrast.resolve
    return ({n: v for n in light if (v := resolve(n, light))}, {n: v for n in dark if (v := resolve(n, dark))})


class PaletteStylesheetTest(unittest.TestCase):
    def test_fallbacks_equal_the_tokens(self):
        """Without the Lumen stylesheet the palette must still look like Lumen, in both modes."""
        css = PALETTE_CSS.read_text(encoding="utf-8")
        light, dark = token_values()
        for selector, values in ((".lm", light), (".lm.is-dark", dark)):
            pairs = FALLBACK_RE.findall(css_block(css, selector))
            self.assertGreater(len(pairs), 5, selector)
            for name, fallback in pairs:
                self.assertEqual(fallback.upper(), values.get(name), f"{selector}: --lm-{name} fallback")

    def test_every_local_variable_is_defined(self):
        css = PALETTE_CSS.read_text(encoding="utf-8")
        defined = set(re.findall(r"(--p-[a-z0-9-]+)\s*:", css_block(css, ".lm")))
        used = set(re.findall(r"var\((--p-[a-z0-9-]+)\)", css))
        self.assertEqual(used - defined, set())

    def test_dark_block_overrides_only_known_variables(self):
        css = PALETTE_CSS.read_text(encoding="utf-8")
        light = set(re.findall(r"(--p-[a-z0-9-]+)\s*:", css_block(css, ".lm")))
        dark = set(re.findall(r"(--p-[a-z0-9-]+)\s*:", css_block(css, ".lm.is-dark")))
        self.assertLessEqual(dark, light)


    def test_the_header_button_keeps_its_name_on_phones(self):
        """display: none on the label would leave an icon-only button without a name (WCAG 4.1.2)."""
        css = re.sub(r"/\*.*?\*/", "", PALETTE_CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            if ".trigger-label" in selectors:
                self.assertNotRegex(body, r"display\s*:\s*none", selectors.strip())
                self.assertNotRegex(body, r"visibility\s*:\s*hidden", selectors.strip())


class NpmManifestTest(unittest.TestCase):
    def setUp(self):
        self.pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    def test_versions_are_exact(self):
        for name, version in self.pkg["devDependencies"].items():
            self.assertRegex(version, r"^\d+\.\d+\.\d+$", f"{name} must be pinned to an exact version")
        self.assertNotIn("dependencies", self.pkg, "the theme ships built files; npm packages are build tools only")

    def test_scripts_point_at_existing_files(self):
        scripts = " ".join(self.pkg["scripts"].values())
        for ref in re.findall(r"(?:--config |node |-p )([\w./-]+\.(?:json|mjs|js))\b", scripts):
            self.assertTrue((ROOT / ref).is_file(), ref)
        for name in ("build", "build:css", "build:island", "build:gallery", "test", "typecheck"):
            self.assertIn(name, self.pkg["scripts"])

    def test_island_and_gallery_outputs(self):
        island = (ROOT / "island" / "vite.config.js").read_text(encoding="utf-8")
        self.assertIn('formats: ["iife"]', island)
        self.assertIn('"lumen-island.js"', island)
        self.assertIn('entry: "island/src/main.ts"', island)
        gallery = (ROOT / "gallery" / "vite.config.js").read_text(encoding="utf-8")
        self.assertIn('base: "./"', gallery)
        self.assertIn('new URL("./dist", import.meta.url)', gallery)


class GalleryVariantTest(unittest.TestCase):
    """The gallery shows Lumen Dark the way the panel does: its own stylesheet on the light base and
    the lumen-night hook class on <html> and <body>, without the panel's dark-mode class."""

    def test_gallery_switches_to_lumen_dark(self):
        app = (ROOT / "gallery" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn('initial("mode", ["light", "dark", "night"] as const, "light")', app)
        self.assertIn('`./lumen-night${rtl ? "-rtl" : ""}.css`', app)
        self.assertIn('document.documentElement.classList.toggle("lumen-night", night);', app)
        self.assertIn('night ? "default-mode lumen-night"', app, "Lumen Dark never sets body.dark-mode")
        self.assertIn("aria-pressed={night}", app)

    def test_token_page_reads_the_pairs_of_the_shown_mode(self):
        page = (ROOT / "gallery" / "src" / "pages" / "Foundations.tsx").read_text(encoding="utf-8")
        self.assertIn("!p.modes || p.modes.includes(mode)", page)
        self.assertIn("isLiteral(name) ? toRgb(name) : readToken(name)", page)


class ContribUnitsTest(unittest.TestCase):
    def unit(self, name: str) -> configparser.ConfigParser:
        cfg = configparser.ConfigParser(strict=False, interpolation=None, delimiters=("=",))
        cfg.optionxform = str  # keep the key case
        cfg.read(ROOT / "contrib" / name, encoding="utf-8")
        return cfg

    def test_service_runs_sync_sandboxed(self):
        svc = self.unit("lumen-panel-sync.service")["Service"]
        self.assertEqual(svc["Type"], "oneshot")
        self.assertRegex(svc["ExecStart"], r"^/usr/bin/python3 -m lumen_panel sync --variant all --keyhelp \S+$")
        self.assertTrue(svc["WorkingDirectory"].endswith("/generator"))
        self.assertEqual(svc["ProtectSystem"], "strict")
        writable = svc["ReadWritePaths"].split()
        keyhelp = svc["ExecStart"].split("--keyhelp ")[1]
        self.assertEqual(set(writable), {f"{keyhelp}/theme", f"{keyhelp}/cache/twig", "/root/backups/lumen-panel"})
        self.assertEqual(svc["PrivateNetwork"], "true")
        self.assertIn("MemoryMax", svc)
        self.assertEqual(svc["ReadOnlyPaths"], f"-{keyhelp}/theme/bulma", "the default theme stays read-only")
        self.assertEqual(svc["CapabilityBoundingSet"].split(), ["CAP_CHOWN", "CAP_DAC_OVERRIDE"])
        for key in ("ProtectProc", "ProcSubset", "PrivateIPC", "RemoveIPC"):
            self.assertIn(key, svc)
        self.assertIn("PYTHONUNBUFFERED=1", (ROOT / "contrib" / "lumen-panel-sync.service").read_text(encoding="utf-8"))
        self.assertEqual(svc["ExecStartPre"], "/bin/sleep 120")
        self.assertEqual(svc["Restart"], "on-failure")
        self.assertNotIn("75", svc["RestartPreventExitStatus"].split(), "exit 75 (try again later) is retried")
        unit = self.unit("lumen-panel-sync.service")["Unit"]
        self.assertIn("AssertPathExists", unit, "a missing build must fail the unit, not skip it")
        self.assertFalse(any(k.startswith("ConditionPathExists") for k in unit))

    def test_path_unit_watches_the_default_theme(self):
        path = self.unit("lumen-panel-sync.path")
        self.assertTrue(path["Path"]["PathChanged"].endswith("/theme/bulma/_settings.json"))
        self.assertEqual(path["Path"]["Unit"], "lumen-panel-sync.service")
        self.assertEqual(path["Install"]["WantedBy"], "paths.target")

    def test_sync_takes_the_options_the_unit_passes(self):
        p = parser()
        svc = self.unit("lumen-panel-sync.service")["Service"]
        args = p.parse_args(svc["ExecStart"].split()[3:])
        self.assertEqual(args.command, "sync")
        self.assertEqual(args.variant, "all", "the unit keeps every installed theme current")
        self.assertEqual(str(args.keyhelp), "/home/keyhelp/www/keyhelp")

    def test_timer_runs_daily_and_catches_up(self):
        timer = self.unit("lumen-panel-sync.timer")
        self.assertRegex(timer["Timer"]["OnCalendar"], r"^\*-\*-\* \d\d:\d\d:\d\d$")
        self.assertEqual(timer["Timer"]["Persistent"], "true")
        self.assertEqual(timer["Install"]["WantedBy"], "timers.target")

    def test_update_doc_explains_the_units(self):
        doc = (ROOT / "docs" / "update.md").read_text(encoding="utf-8")
        for needle in ("contrib/lumen-panel-sync.service", "contrib/lumen-panel-sync.timer",
                       "contrib/lumen-panel-sync.path", "systemctl enable --now lumen-panel-sync.path",
                       "systemctl enable --now lumen-panel-sync.timer", "python3 -m lumen_panel sync",
                       "chown -R root:root /opt/lumen-panel"):
            self.assertIn(needle, doc)


def repo_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, check=True)
    return [ROOT / p for p in out.stdout.decode("utf-8").split("\0") if p and (ROOT / p).is_file()]


@unittest.skipUnless(KEYHELP_THEME.is_dir(), "no KeyHelp installation on this machine")
class NoKeyHelpFilesTest(unittest.TestCase):
    """The licence rule as a test: KeyHelp's files are read on the server, never committed.
    Reads the installed default theme only (read-only)."""

    MIN_LINE = 60
    # Standard HTML boilerplate that every web page shares; not an excerpt of the templates.
    BOILERPLATE = {'<meta name="viewport" content="width=device-width, initial-scale=1">'}

    def test_no_repository_file_is_a_copy_of_a_default_theme_file(self):
        theirs = {hashlib.sha256(p.read_bytes()).hexdigest(): p
                  for p in KEYHELP_THEME.rglob("*") if p.is_file() and not p.is_symlink() and p.stat().st_size > 0}
        for path in repo_files():
            if path.stat().st_size == 0:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertNotIn(digest, theirs, f"{path.relative_to(ROOT)} is a copy of {theirs.get(digest)}")

    def test_no_long_template_line_is_quoted(self):
        lines: set[str] = set()
        for twig in (KEYHELP_THEME / "templates").rglob("*.twig"):
            for line in twig.read_text(encoding="utf-8", errors="replace").splitlines():
                if len(line.strip()) >= self.MIN_LINE and line.strip() not in self.BOILERPLATE:
                    lines.add(line.strip())
        self.assertGreater(len(lines), 100)
        for path in repo_files():
            if path.suffix in {".png", ".ttf", ".svg", ".woff2"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            quoted = [line for line in (raw.strip() for raw in text.splitlines()) if line in lines]
            self.assertEqual(quoted, [], f"{path.relative_to(ROOT)} quotes the default theme")


if __name__ == "__main__":
    unittest.main()
