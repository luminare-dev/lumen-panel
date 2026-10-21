"""Tests for the two theme variants, Lumen and Lumen Dark: what each build holds, that the two stay
fully separate on disk (folders, staging names, backups, locks, holds, Twig cache entries), and the
Pro boundary of Lumen Dark (it never loads, enables or imitates the panel's own dark mode).

Everything runs against a fake KeyHelp tree in a temporary folder (tests/fakekeyhelp.py).
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))
sys.path.insert(0, str(ROOT / "tests"))

import fakekeyhelp as fk  # noqa: E402
from test_generator import Env, lines  # noqa: E402 (Env has no tests of its own)
from lumen_panel import cli, variants  # noqa: E402
from lumen_panel import install as inst  # noqa: E402
from lumen_panel.build import BuildError, asset_hash, build, theme_assets  # noqa: E402
from lumen_panel.patches import PatchError, load_patches, patch_files, patch_set_sha256  # noqa: E402
from lumen_panel.twig import asset_references  # noqa: E402
from lumen_panel.variants import LUMEN, LUMEN_DARK, PRO_DARK_MODE_MARKERS, VARIANTS  # noqa: E402
from lumen_panel.verify import verify  # noqa: E402

STYLES = ROOT / "src" / "styles"
DIST = ROOT / "dist" / "assets"
# A Twig assignment to the panel's dark-mode switch ({% set _app.theme.is_dark_mode = ... %} and the
# like), or a theme setting that claims a dark mode.
FORCE_RE = re.compile(r"\{%-?\s*set\s[^%]*\b(?:is_dark_mode|has_dark_mode)\b")


def dark_stylesheets(src: str) -> list[str]:
    """Every default-theme stylesheet a template can load that is one of its dark builds."""
    return [r for r in asset_references(src, "bulma") if r.startswith("assets/css/") and "-dark" in r]


class VariantDefinitionTest(unittest.TestCase):
    def test_the_two_variants(self):
        self.assertEqual(list(VARIANTS), ["lumen", "lumen-dark"])
        self.assertIs(variants.DEFAULT_VARIANT, LUMEN)
        self.assertEqual((LUMEN.dir_name, LUMEN.display_name, LUMEN.has_dark_mode), ("lumen", "Lumen", True))
        self.assertEqual((LUMEN_DARK.dir_name, LUMEN_DARK.display_name, LUMEN_DARK.has_dark_mode),
                         ("lumen-dark", "Lumen Dark", False))
        for v in VARIANTS.values():
            self.assertNotIn("KeyHelp", v.display_name)
            self.assertNotIn("KeyHelp", v.dir_name)
            self.assertIn("Not affiliated with or endorsed by Keyweb AG", v.description)
            self.assertTrue(v.screenshot_file.is_file(), v.screenshot_file)

    def test_lumen_dark_says_it_is_not_the_pro_dark_mode(self):
        self.assertIn("not the dark mode of KeyHelp Pro", LUMEN_DARK.description)
        self.assertIn("does not enable, unlock or imitate it", LUMEN_DARK.description)
        self.assertIn("standard light stylesheet", LUMEN_DARK.description)

    def test_names_never_overlap(self):
        """No prefix of one variant matches a folder of the other: leftovers stay with their variant."""
        names = [LUMEN.dir_name, LUMEN_DARK.dir_name]
        for v in VARIANTS.values():
            others = [o for o in VARIANTS.values() if o is not v]
            for o in others:
                for prefix in v.leftover_prefixes:
                    for folder in (o.staging_prefix + "20261021T000000000000Z", o.parking_prefix + "x"):
                        self.assertFalse(folder.startswith(prefix), (prefix, folder))
            self.assertNotIn("bulma", names)
        self.assertEqual(set(LUMEN.stylesheets) & set(LUMEN_DARK.stylesheets), set())

    def test_backup_folders_and_cli_args(self):
        root = Path("/root/backups/lumen-panel")
        self.assertEqual(LUMEN.backup_root(root), root, "Lumen keeps the backup folder it always had")
        self.assertEqual(LUMEN_DARK.backup_root(root), root / "lumen-dark")
        self.assertEqual(LUMEN.cli_args, "")
        self.assertEqual(LUMEN_DARK.cli_args, " --variant lumen-dark")


class PatchSetTest(unittest.TestCase):
    def test_overlay_replaces_by_name_and_adds(self):
        base = [s for s, _ in patch_files(fk.PATCHES)]
        dark = [s for s, _ in patch_files(fk.PATCHES, "lumen-dark")]
        self.assertTrue(all("/" not in s for s in base))
        self.assertIn("lumen-dark/10-base-stylesheet.json", dark)
        self.assertNotIn("10-base-stylesheet.json", dark)
        self.assertIn("20-base-island-block.json", dark, "shared patches stay single-sourced")
        self.assertIn("30-intern-island.json", dark)
        self.assertEqual([Path(s).name for s in dark], sorted(Path(s).name for s in dark), "applied in name order")
        ids = [p.id for p in load_patches(fk.PATCHES, "lumen-dark")]
        self.assertEqual(len(ids), len(set(ids)))
        for wanted in ("night-default-stylesheet", "night-color-scheme", "night-html-class", "night-body-class"):
            self.assertIn(wanted, ids)

    def test_lumen_patch_hash_ignores_the_overlay_folder(self):
        """Lumen's patch-set hash is computed over patches/*.json only, as before Lumen Dark."""
        import hashlib

        digest = hashlib.sha256()
        for path in sorted(fk.PATCHES.glob("*.json")):
            digest.update(path.name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
        self.assertEqual(patch_set_sha256(fk.PATCHES), digest.hexdigest())
        self.assertNotEqual(patch_set_sha256(fk.PATCHES, "lumen-dark"), patch_set_sha256(fk.PATCHES))

    def test_missing_overlay_fails_loudly(self):
        with self.assertRaises(PatchError):
            load_patches(fk.PATCHES, "no-such-variant")

    def test_theme_paths_use_the_folder_token(self):
        """A path to the theme's own files never names a folder: one variant must never load the
        other's files (they are installed and removed independently)."""
        for v in VARIANTS.values():
            for p in load_patches(fk.PATCHES, v.patch_overlay):
                self.assertNotRegex(p.text, r"/theme/lumen", f"{p.source}: use /theme/@@LUMEN_THEME_DIR@@/")


class ProBoundaryTest(Env):
    """Lumen Dark is a dark design of its own on top of the panel's standard (light) stylesheet:
    it never loads the default theme's dark stylesheets, never sets the dark-mode switch and never
    uses the 'dark/' images. These checks fail if any of that changes."""

    def test_lumen_dark_patch_texts_never_use_the_dark_mode(self):
        for p in load_patches(fk.PATCHES, LUMEN_DARK.patch_overlay):
            for m in PRO_DARK_MODE_MARKERS:
                self.assertNotIn(m, p.text, f"{p.source} [{p.id}]")
            self.assertNotRegex(p.text, FORCE_RE)

    def test_built_lumen_dark_never_loads_a_dark_stylesheet_or_sets_the_switch(self):
        out = build(self.kh, self.tmp / "lumen-dark", variant=LUMEN_DARK, assets_dir=self.assets,
                    screenshot_fallback=self.shot).out_dir
        settings = json.loads((out / "_settings.json").read_text(encoding="utf-8"))
        self.assertIs(settings["has_dark_mode"], False)
        self.assertIn('"has_dark_mode": false', (out / "_settings.json").read_text(encoding="utf-8"))
        for twig in (out / "templates").rglob("*.twig"):
            text = twig.read_text(encoding="utf-8")
            self.assertEqual(dark_stylesheets(text), [], twig)
            self.assertNotRegex(text, FORCE_RE, twig)
        base = (out / "templates" / "layout" / "base.twig").read_text(encoding="utf-8")
        self.assertIn("/theme/bulma/assets/css/style{{ _app.text_direction == 'rtl' ? '-rtl' }}.css", base)
        self.assertEqual([r for r in asset_references(base, "bulma") if r.startswith("assets/css/")],
                         ["assets/css/style-rtl.css", "assets/css/style.css"])
        report = verify(out, self.kh)
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(any(p.startswith("pro boundary") for p in report.passed), report.passed)

    def test_verify_catches_a_dark_stylesheet_and_a_dark_mode_patch(self):
        patches = self.tmp / "patches"
        shutil.copytree(fk.PATCHES, patches)
        sneaky = patches / "lumen-dark" / "13-night-html-class.json"
        data = json.loads(sneaky.read_text(encoding="utf-8"))
        data["text"] = data["text"].replace('class="lumen-night"', "class=\"{{ _app.theme.is_dark_mode ? 'x' }}\"")
        sneaky.write_text(json.dumps(data), encoding="utf-8")
        out = build(self.kh, self.tmp / "lumen-dark", variant=LUMEN_DARK, patches_dir=patches, assets_dir=self.assets,
                    screenshot_fallback=self.shot).out_dir
        errors = "\n".join(verify(out, self.kh).errors)
        self.assertIn("night-html-class: its text uses is_dark_mode", errors)

        good = build(self.kh, self.tmp / "again" / "lumen-dark", variant=LUMEN_DARK, assets_dir=self.assets,
                     screenshot_fallback=self.shot).out_dir
        extra = good / "templates" / "layout" / "views.twig"
        extra.write_text("<link href=\"/theme/bulma/assets/css/style{{ _app.theme.is_dark_mode ? '-dark' }}.css\">",
                         encoding="utf-8")
        errors = "\n".join(verify(good).errors)
        self.assertIn("can load the default theme's dark stylesheet theme/bulma/assets/css/style-dark.css", errors)

    def test_lumen_dark_css_never_uses_the_panel_dark_assets(self):
        """lumen-night.css is index.css + the dark tokens + night.css (+ rtl.css): none of them may
        load or name the default theme's dark stylesheets or its 'dark/' images."""
        sources = sorted(STYLES.rglob("*.css"))
        built = sorted(DIST.glob("lumen-night*.css")) if DIST.is_dir() else []
        self.assertTrue(sources)
        for path in sources + built:
            css = path.read_text(encoding="utf-8")
            for needle in ("style-dark", "img/dark", "/theme/bulma/", "is_dark_mode", "has_dark_mode"):
                self.assertNotIn(needle, css, f"{path.relative_to(ROOT)}: {needle}")


class BuildTest(Env):
    def test_lumen_dark_build(self):
        out = build(self.kh, self.tmp / "lumen-dark", variant=LUMEN_DARK, assets_dir=self.assets,
                    screenshot_fallback=self.shot).out_dir
        settings = json.loads((out / "_settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["name"], "Lumen Dark")
        self.assertEqual(settings["description"], LUMEN_DARK.description)
        self.assertEqual(settings["path_to_templates"], "templates/")
        manifest = json.loads((out / "_lumen_build.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["variant"], "lumen-dark")
        self.assertEqual(manifest["substitutions"]["LUMEN_THEME_DIR"], "lumen-dark")
        self.assertEqual(manifest["patches_sha256"], patch_set_sha256(fk.PATCHES, "lumen-dark"))
        css = sorted(p.name for p in (out / "assets").glob("*.css"))
        self.assertEqual(css, ["lumen-night-rtl.css", "lumen-night.css"], "only Lumen Dark's stylesheets")
        self.assertTrue((out / "assets" / "lumen-island.js").is_file())
        self.assertIn("always dark", (out / "LUMEN-README.txt").read_text(encoding="utf-8"))
        self.assertIn("sync --variant lumen-dark", (out / "LUMEN-README.txt").read_text(encoding="utf-8"))
        base = (out / "templates" / "layout" / "base.twig").read_text(encoding="utf-8")
        self.assertIn('<html class="lumen-night" lang=', base)
        self.assertRegex(base, r"<body class=\"[^\"]*\{# lumen-panel:night-body-class #\} lumen-night\">")
        self.assertIn('<meta name="color-scheme" content="dark">', base)
        self.assertEqual(asset_references(base, "lumen-dark"), ["assets/lumen-night-rtl.css", "assets/lumen-night.css"])
        self.assertEqual(asset_references(base, "lumen"), [])
        for rel in ("layout/intern.twig", "layout/extern.twig", "layout/popup.twig"):
            text = (out / "templates" / rel).read_text(encoding="utf-8")
            self.assertNotIn("-light.svg", text, rel)
            self.assertEqual(asset_references(text, "lumen"), [], rel)
            for ref in asset_references(text, "lumen-dark"):
                self.assertTrue(ref.endswith("-dark.svg") or ref == "assets/lumen-island.js", ref)
        self.assertTrue(verify(out, self.kh).ok)
        self.assertTrue(verify(out).ok)
        self.assertTrue(verify(out, self.kh, variant=LUMEN_DARK).ok)

    def test_lumen_build_takes_only_its_own_stylesheets(self):
        out = self.build_to(self.tmp / "lumen").out_dir
        css = sorted(p.name for p in (out / "assets").glob("*.css"))
        self.assertEqual(css, ["lumen-dark-rtl.css", "lumen-dark.css", "lumen-rtl.css", "lumen.css"])
        manifest = json.loads((out / "_lumen_build.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["variant"], "lumen")
        self.assertNotIn("lumen-night", (out / "templates" / "layout" / "base.twig").read_text(encoding="utf-8"))

    def test_asset_hash_covers_only_the_variants_files(self):
        lumen, dark = asset_hash(self.assets, LUMEN), asset_hash(self.assets, LUMEN_DARK)
        self.assertNotEqual(lumen, dark)
        night = self.assets / "lumen-night.css"
        night.write_text(night.read_text(encoding="utf-8") + "a{}\n", encoding="utf-8")
        self.assertEqual(asset_hash(self.assets, LUMEN), lumen, "Lumen does not change with Lumen Dark's CSS")
        self.assertNotEqual(asset_hash(self.assets, LUMEN_DARK), dark)
        self.assertNotIn("lumen.css", theme_assets(self.assets, LUMEN_DARK))
        self.assertNotIn("lumen-night.css", theme_assets(self.assets, LUMEN))

    def test_assets_of_lumen_dark_are_required_and_strays_still_stop(self):
        (self.assets / "lumen-night-rtl.css").unlink()
        with self.assertRaises(BuildError) as ctx:
            build(self.kh, self.tmp / "lumen-dark", variant=LUMEN_DARK, assets_dir=self.assets,
                  screenshot_fallback=self.shot)
        self.assertIn("lumen-night-rtl.css", str(ctx.exception))
        self.build_to(self.tmp / "lumen")   # Lumen does not need Lumen Dark's files
        (self.assets / "lumen-other.css").write_text("x", encoding="utf-8")
        with self.assertRaises(BuildError) as ctx:
            self.build_to(self.tmp / "lumen2")
        self.assertIn("lumen-other.css", str(ctx.exception))

    def test_verify_keeps_the_variants_apart(self):
        out = build(self.kh, self.tmp / "x" / "lumen-dark", variant=LUMEN_DARK, assets_dir=self.assets,
                    screenshot_fallback=self.shot).out_dir
        self.assertIn("a build of 'Lumen Dark', expected 'Lumen'", "\n".join(verify(out, variant=LUMEN).errors))
        wrong_folder = self.tmp / "y" / "lumen"
        shutil.copytree(out, wrong_folder)
        self.assertIn("the folder of 'Lumen' holds a build of 'Lumen Dark'", "\n".join(verify(wrong_folder).errors))
        intern = out / "templates" / "layout" / "intern.twig"
        intern.write_text(intern.read_text(encoding="utf-8") + '<img src="/theme/lumen/assets/brand/x.svg">',
                          encoding="utf-8")
        self.assertIn("refers to theme/lumen/assets/brand/x.svg, the folder of 'Lumen'",
                      "\n".join(verify(out).errors))
        settings = out / "_settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        data["has_dark_mode"] = True
        settings.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("_settings.json: unexpected or missing has_dark_mode", "\n".join(verify(out).errors))


class SeparationTest(Env):
    """Both variants in one panel: every command touches only its own variant."""

    def setUp(self):
        super().setUp()
        self.dark = inst.Options(assets_dir=self.assets, screenshot_fallback=self.shot,
                                 backup_root=self.tmp / "backups", owner="", variant=LUMEN_DARK)
        self.dark_theme = self.kh / "theme" / "lumen-dark"
        self.backups = self.tmp / "backups"

    def at(self, suffix: str):
        return mock.patch.object(inst, "timestamp", return_value=inst.timestamp()[:-1] + suffix)

    def theme_dirs(self) -> list[str]:
        return sorted(p.name for p in (self.kh / "theme").iterdir())

    def test_both_installed_side_by_side(self):
        with self.at("1Z"):
            code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        with self.at("2Z"):
            code, out = lines(inst.install, self.kh, options=self.dark)
        self.assertEqual(code, 0, out)
        self.assertIn("select 'Lumen Dark' and save", out)
        self.assertIn("uninstall --variant lumen-dark --keyhelp", out)
        self.assertEqual(self.theme_dirs(), ["bulma", "lumen", "lumen-dark"])
        self.assertTrue(verify(self.lumen, self.kh).ok)
        self.assertTrue(verify(self.dark_theme, self.kh).ok)
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["name"], "Lumen")
        self.assertEqual(json.loads((self.dark_theme / "_settings.json").read_text())["name"], "Lumen Dark")
        # own backup folders, own locks
        self.assertTrue((self.backups / ".lock").is_file())
        self.assertTrue((self.backups / "lumen-dark" / ".lock").is_file())
        self.assertTrue(any(p.name.endswith("2Z") for p in (self.backups / "lumen-dark").iterdir()))
        self.assertFalse(any(p.name.endswith("2Z") for p in self.backups.iterdir()))
        self.assertEqual((self.backups / "lumen-dark").stat().st_mode & 0o777, 0o700)
        # ROLLBACK.txt of Lumen Dark always names the variant
        text = next((self.backups / "lumen-dark").glob("*/ROLLBACK.txt")).read_text(encoding="utf-8")
        for line in text.splitlines():
            if "python3 -m lumen_panel" in line:
                self.assertIn("--variant lumen-dark", line)

    def test_cache_leftovers_and_reinstall_stay_with_their_variant(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.install, self.kh, options=self.dark)[0], 0)
        lumen_entry = fk.compiled_entry(self.cache, "aa" + "1" * 30, f"{self.lumen.resolve()}/templates/layout/base.twig")
        dark_entry = fk.compiled_entry(self.cache, "ab" + "2" * 30,
                                       f"{self.dark_theme.resolve()}/templates/layout/base.twig")
        dark_rel = fk.compiled_entry(self.cache, "ac" + "3" * 30, "theme/lumen-dark/templates/layout/intern.twig")
        bulma_entry = fk.compiled_entry(self.cache, "ad" + "4" * 30, f"{self.bulma.resolve()}/templates/layout/base.twig")
        for name in (".lumen-staging-20261021T030000000000Z", ".lumen-dark-staging-20261021T030000000000Z"):
            (self.kh / "theme" / name).mkdir()
        fk.set_version(self.kh, "26.2.0")
        with self.at("3Z"):
            code, out = lines(inst.install, self.kh, options=self.dark)
        self.assertEqual(code, 0, out)
        self.assertFalse(dark_entry.exists())
        self.assertFalse(dark_rel.exists())
        self.assertTrue(lumen_entry.exists(), "Lumen's compiled templates stay")
        self.assertTrue(bulma_entry.exists())
        self.assertIn(".lumen-staging-20261021T030000000000Z", self.theme_dirs(), "Lumen's leftover stays")
        self.assertNotIn(".lumen-dark-staging-20261021T030000000000Z", self.theme_dirs())
        saved = next((self.backups / "lumen-dark").glob("*3Z"))
        self.assertTrue((saved / "lumen-dark" / "_settings.json").is_file())
        self.assertEqual(len(list((saved / "twig-cache").rglob("*.php"))), 2)
        self.assertTrue((saved / "stale" / ".lumen-dark-staging-20261021T030000000000Z").is_dir())
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.1.1",
                         "Lumen is not rebuilt by a Lumen Dark install")

    def test_hold_rollback_and_check_update_are_per_variant(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        with self.at("4Z"):
            self.assertEqual(lines(inst.install, self.kh, options=self.dark)[0], 0)
        first_dark = next((self.backups / "lumen-dark").glob("*4Z"))
        fk.set_version(self.kh, "26.1.3")
        with self.at("5Z"):
            self.assertEqual(lines(inst.install, self.kh, options=self.dark)[0], 0)
        second_dark = next((self.backups / "lumen-dark").glob("*5Z"))
        # a Lumen Dark backup never goes back as Lumen, and the other way round
        with self.assertRaises(inst.InstallError) as ctx:
            inst.rollback(self.kh, second_dark, options=self.options, out=lambda _l: None)
        self.assertIn("no saved Lumen theme here", str(ctx.exception))
        with self.assertRaises(inst.InstallError) as ctx:
            inst.rollback(self.kh, second_dark / "lumen-dark", options=self.options, out=lambda _l: None)
        self.assertIn("a saved 'Lumen Dark' theme, not 'Lumen'", str(ctx.exception))
        code, out = lines(inst.rollback, self.kh, second_dark, options=self.dark)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.dark_theme / "_settings.json").read_text())["lumen_base_version"], "26.1.1")
        self.assertTrue((self.backups / "lumen-dark" / "HOLD").is_file())
        self.assertFalse((self.backups / "HOLD").exists(), "Lumen is not held")
        code, out = lines(inst.check_update, self.kh, options=self.dark)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("run install --variant lumen-dark to resume", out)
        code, out = lines(inst.sync, self.kh, options=self.dark)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.dark_theme / "_settings.json").read_text())["lumen_base_version"], "26.1.1",
                         "the held variant is not rebuilt")
        code, out = lines(inst.sync, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.1.3",
                         "Lumen still follows the panel")
        self.assertEqual(lines(inst.release, self.dark)[0], 0)
        self.assertFalse((self.backups / "lumen-dark" / "HOLD").exists())
        self.assertTrue(first_dark.is_dir())

    def test_check_update_compares_each_variants_assets_and_patches(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.install, self.kh, options=self.dark)[0], 0)
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        code, out = lines(inst.check_update, self.kh, options=self.dark)
        self.assertEqual(code, 0, out)
        self.assertIn("up to date (Lumen Dark, default theme 26.1.1", out)
        night = self.assets / "lumen-night.css"
        night.write_text(night.read_text(encoding="utf-8") + "a{}\n", encoding="utf-8")
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        code, out = lines(inst.check_update, self.kh, options=self.dark)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("built assets changed", out)
        self.assertEqual(lines(inst.sync, self.kh, options=self.dark)[0], 0)
        patches = self.tmp / "patches"
        shutil.copytree(fk.PATCHES, patches)
        overlay = patches / "lumen-dark" / "12-night-color-scheme.json"
        overlay.write_text(overlay.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        for opts, want in ((self.options, 0), (self.dark, inst.EXIT_REBUILD_NEEDED)):
            code, out = lines(inst.check_update, self.kh, options=inst.Options(
                patches_dir=patches, assets_dir=self.assets, backup_root=self.backups, variant=opts.variant))
            self.assertEqual(code, want, out)

    def test_uninstall_one_keeps_the_other(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.install, self.kh, options=self.dark)[0], 0)
        page = b'<link href="/theme/bulma/assets/css/style.css?1"><link href="/theme/lumen-dark/assets/lumen-night.css?v=1">'

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        with mock.patch("urllib.request.urlopen", return_value=Resp(page)):
            self.assertIs(inst.detect_active("https://panel.example.org/", variant=LUMEN_DARK), True)
        with mock.patch("urllib.request.urlopen", return_value=Resp(page)):
            self.assertIs(inst.detect_active("https://panel.example.org/", variant=LUMEN), False)
        with mock.patch("urllib.request.urlopen", return_value=Resp(page)):
            code, out = lines(inst.uninstall, self.kh, options=self.dark, panel_url="https://panel.example.org/")
        self.assertEqual(code, inst.EXIT_ACTIVE)
        self.assertIn("still loads the Lumen Dark stylesheet", out)
        with self.at("6Z"):
            code, out = lines(inst.uninstall, self.kh, options=self.dark, confirmed=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.theme_dirs(), ["bulma", "lumen"])
        self.assertTrue(verify(self.lumen, self.kh).ok)
        backup = next((self.backups / "lumen-dark").glob("*6Z"))
        self.assertTrue((backup / "lumen-dark" / "_settings.json").is_file())
        self.assertIn("rollback --variant lumen-dark", (backup / "ROLLBACK.txt").read_text(encoding="utf-8"))
        code, out = lines(inst.check_update, self.kh, options=self.dark)
        self.assertEqual(code, inst.EXIT_NOT_INSTALLED)

    def test_dry_run_of_lumen_dark_writes_nothing(self):
        code, out = lines(inst.install, self.kh, dry_run=True, options=self.dark)
        self.assertEqual(code, 0, out)
        self.assertIn("Lumen Dark, default theme 26.1.1, 11 patches", out)
        self.assertIn(f"swap it in at {self.dark_theme}", out)
        self.assertIn(str(self.backups / "lumen-dark"), out)
        self.assertEqual(self.theme_dirs(), ["bulma"])
        self.assertFalse(self.backups.exists())

    def cli(self, *args: str) -> tuple[int, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main([*args, "--keyhelp", str(self.kh), "--assets", str(self.assets),
                             "--backup-root", str(self.backups)] + (["--screenshot", str(self.shot), "--owner", ""]
                                                                     if args[0] in ("install", "sync") else []))
        return code, stdout.getvalue() + stderr.getvalue()

    def test_cli_variant_all(self):
        code, out = self.cli("sync", "--variant", "all")
        self.assertEqual(code, 0, out)
        self.assertIn("Lumen Dark is not installed", out)
        self.assertFalse(self.backups.exists(), "nothing installed: no lock, no backup folder")
        self.assertEqual(self.cli("check-update", "--variant", "all")[0], inst.EXIT_NOT_INSTALLED)
        self.assertEqual(self.cli("install", "--variant", "lumen-dark")[0], 0)
        code, out = self.cli("check-update", "--variant", "all")
        self.assertEqual(code, 0, out)
        self.assertIn("== Lumen Dark (theme/lumen-dark)", out)
        fk.set_version(self.kh, "26.2.0")
        self.assertEqual(self.cli("check-update", "--variant", "all")[0], inst.EXIT_REBUILD_NEEDED)
        code, out = self.cli("sync", "--variant", "all")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.dark_theme / "_settings.json").read_text())["lumen_base_version"], "26.2.0")
        self.assertFalse(self.lumen.exists(), "sync never installs a variant that is not installed")
        self.assertEqual(self.cli("check-update", "--variant", "all")[0], 0)

    def test_cli_variant_all_reports_the_worst_result(self):
        self.assertEqual(self.cli("install")[0], 0)
        self.assertEqual(self.cli("install", "--variant", "lumen-dark")[0], 0)
        fk.set_version(self.kh, "26.2.0")
        with inst.run_lock(self.options):            # Lumen busy: Lumen Dark still syncs
            code, out = self.cli("sync", "--variant", "all")
        self.assertEqual(code, inst.EXIT_TEMPFAIL, out)
        self.assertEqual(json.loads((self.dark_theme / "_settings.json").read_text())["lumen_base_version"], "26.2.0")
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.1.1")

    def test_cli_verify_reads_the_variant_from_the_build_record(self):
        self.assertEqual(self.cli("install", "--variant", "lumen-dark")[0], 0)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(cli.main(["verify", str(self.dark_theme), "--keyhelp", str(self.kh)]), 0)
            self.assertEqual(cli.main(["verify", str(self.dark_theme), "--variant", "lumen-dark"]), 0)
            self.assertEqual(cli.main(["verify", str(self.dark_theme), "--variant", "lumen"]), 1)
        self.assertIn("ok: pro boundary", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
