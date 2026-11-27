"""Customizations: checking a customizer ZIP, building with it, apply-custom (fake panel tree)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))
sys.path.insert(0, str(ROOT / "tests"))

import fakekeyhelp as fk  # noqa: E402
from test_generator import Env, lines  # noqa: E402 (Env has no tests of its own)
from lumen_panel import apply, custom  # noqa: E402
from lumen_panel import install as inst  # noqa: E402
from lumen_panel.build import BuildError, build  # noqa: E402
from lumen_panel.variants import LUMEN, LUMEN_DARK, VARIANTS  # noqa: E402
from lumen_panel.verify import verify  # noqa: E402

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="10"><rect width="40" height="10"/></svg>\n'
CSS = "/* Lumen tokens v1: Test */\n:root {\n    --lumen-accent: #123456;\n}\n"


def make_custom(folder: Path, **branding: str) -> Path:
    folder.mkdir(parents=True)
    (folder / "lumen.tokens.json").write_text(json.dumps({"version": 1, "meta": {"name": "Test"}}), encoding="utf-8")
    (folder / "override-follow.css").write_text(CSS + "/* follow */\n", encoding="utf-8")
    (folder / "override-dark.css").write_text(CSS + "/* dark */\n", encoding="utf-8")
    (folder / "custom").mkdir()
    (folder / "custom" / "logo.svg").write_bytes(SVG)
    (folder / "custom" / "fav.png").write_bytes(fk.tiny_png())
    values = {"headerLight": "custom/logo.svg", "headerDark": "custom/logo.svg", "loginLight": "custom/logo.svg",
              "loginDark": "custom/logo.svg", "favicon": "custom/fav.png", "productName": "Example Hosting"}
    values.update(branding)
    (folder / "branding.json").write_text(json.dumps(values), encoding="utf-8")
    return folder


def zip_folder(folder: Path, dest: Path, prefix: str = "") -> Path:
    with zipfile.ZipFile(dest, "w") as z:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                z.write(path, prefix + path.relative_to(folder).as_posix())
    return dest


class LoadTest(Env):
    def test_a_good_folder_loads(self):
        c = custom.load(make_custom(self.tmp / "c"), self.assets)
        self.assertEqual(c.name, "Test")
        self.assertEqual(c.media, ("fav.png", "logo.svg"))
        self.assertEqual(c.branding["productName"], "Example Hosting")

    def test_problems_are_listed(self):
        folder = make_custom(self.tmp / "c", headerLight="custom/missing.png", favicon='https://x.example/"onload')
        (folder / "custom" / "logo.svg").write_bytes(b'<svg><script>alert(1)</script></svg>')
        (folder / "notes.md").write_text("x", encoding="utf-8")
        with self.assertRaises(custom.CustomError) as ctx:
            custom.load(folder, self.assets)
        text = "\n".join(ctx.exception.problems)
        self.assertIn("notes.md: unexpected file", text)
        (folder / "notes.md").unlink()
        with self.assertRaises(custom.CustomError) as ctx:
            custom.load(folder, self.assets)
        text = "\n".join(ctx.exception.problems)
        self.assertIn("custom/logo.svg: not an SVG, or it contains scripts", text)
        self.assertIn("headerLight names custom/missing.png", text)
        self.assertIn("favicon must be", text)

    def test_svg_with_external_reference_or_wrong_type_is_refused(self):
        folder = make_custom(self.tmp / "c")
        (folder / "custom" / "logo.svg").write_bytes(b'<svg><image href="https://x.example/a.png"/></svg>')
        (folder / "custom" / "fav.png").write_bytes(b"GIF89a....")
        with self.assertRaises(custom.CustomError) as ctx:
            custom.load(folder, self.assets)
        self.assertEqual(len(ctx.exception.problems), 2)

    def test_css_must_be_a_compiled_override(self):
        folder = make_custom(self.tmp / "c")
        (folder / "override-dark.css").write_text("body{}</style><script>", encoding="utf-8")
        with self.assertRaises(custom.CustomError):
            custom.load(folder, self.assets)

    def test_zip_paths_are_not_trusted(self):
        bad = self.tmp / "bad.zip"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("../evil.txt", "x")
            z.writestr("lumen.tokens.json", "{}")
        dest = self.tmp / "out"
        dest.mkdir()
        with self.assertRaises(custom.CustomError):
            custom.extract_zip(bad, dest)
        self.assertFalse((self.tmp / "evil.txt").exists())

    def test_zip_with_one_top_folder(self):
        z = zip_folder(make_custom(self.tmp / "c"), self.tmp / "c.zip", prefix="lumen-test/")
        dest = self.tmp / "out"
        dest.mkdir()
        c = custom.load(custom.extract_zip(z, dest), self.assets)
        self.assertEqual(c.name, "Test")


class BuildWithCustomTest(Env):
    def test_lumen_build_uses_the_customization(self):
        folder = make_custom(self.tmp / "c")
        out = self.tmp / "out"
        result = build(self.kh, out, assets_dir=self.assets, screenshot_fallback=self.shot, custom_dir=folder)
        self.assertEqual(result.custom_name, "Test")
        css = (out / "assets" / "lumen.css").read_text(encoding="utf-8")
        self.assertTrue(css.endswith("/* follow */\n"))
        self.assertTrue((out / "assets" / "lumen-dark.css").read_text(encoding="utf-8").endswith("/* dark */\n"))
        self.assertEqual((out / "assets" / "custom" / "logo.svg").read_bytes(), SVG)
        intern = (out / "templates" / "layout" / "intern.twig").read_text(encoding="utf-8")
        self.assertIn('src="/theme/lumen/assets/custom/logo.svg?v=', intern)
        self.assertIn('alt="Example Hosting"', intern)
        base = (out / "templates" / "layout" / "base.twig").read_text(encoding="utf-8")
        self.assertIn('<link rel="icon" type="image/png" href="/theme/lumen/assets/custom/fav.png?v=', base)
        manifest = json.loads((out / "_lumen_build.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["custom"]["files"], ["custom/fav.png", "custom/logo.svg"])
        self.assertNotEqual(manifest["substitutions"]["LUMEN_ASSET_HASH"], manifest["asset_hash"])
        report = verify(out, self.kh, variant=LUMEN)
        self.assertTrue(report.ok, report.errors)

    def test_empty_logos_bring_back_the_panel_logo_or_a_name(self):
        folder = make_custom(self.tmp / "c", headerLight="", headerDark="", loginLight="", loginDark="", favicon="")
        for v in VARIANTS.values():
            out = self.tmp / v.name
            build(self.kh, out, variant=v, assets_dir=self.assets, screenshot_fallback=self.shot, custom_dir=folder)
            intern = (out / "templates" / "layout" / "intern.twig").read_text(encoding="utf-8")
            if v.has_dark_mode:
                self.assertIn(custom.KEYHELP_LOGO, intern)
            else:
                self.assertIn('<span class="lumen-logo lumen-logo--header lumen-logo--text">Example Hosting</span>', intern)
            report = verify(out, self.kh, variant=v)
            self.assertTrue(report.ok, report.errors)

    def test_different_logos_per_mode_in_lumen_and_the_dark_one_in_lumen_dark(self):
        folder = make_custom(self.tmp / "c", headerLight="brand/luminare-lockup-compact-light.svg")
        out = self.tmp / "lumen"
        build(self.kh, out, assets_dir=self.assets, screenshot_fallback=self.shot, custom_dir=folder)
        intern = (out / "templates" / "layout" / "intern.twig").read_text(encoding="utf-8")
        self.assertIn("{% if _app.theme.is_dark_mode %}", intern)
        self.assertIn('width="127" height="42" alt="Example Hosting"', intern)
        out = self.tmp / "dark"
        build(self.kh, out, variant=LUMEN_DARK, assets_dir=self.assets, screenshot_fallback=self.shot,
              custom_dir=folder)
        intern = (out / "templates" / "layout" / "intern.twig").read_text(encoding="utf-8")
        self.assertNotIn("is_dark_mode", intern.split("{# lumen-panel:intern-logo #}")[1].split(">")[0])
        self.assertTrue(verify(out, self.kh, variant=LUMEN_DARK).ok)

    def test_a_bad_customization_stops_the_build(self):
        folder = make_custom(self.tmp / "c", favicon="custom/nope.ico")
        with self.assertRaises(BuildError):
            build(self.kh, self.tmp / "out", assets_dir=self.assets, screenshot_fallback=self.shot, custom_dir=folder)
        self.assertFalse((self.tmp / "out").exists() and any((self.tmp / "out").iterdir()))

    def test_without_customization_nothing_changes(self):
        out = self.tmp / "out"
        build(self.kh, out, assets_dir=self.assets, screenshot_fallback=self.shot, custom_dir=self.tmp / "none")
        intern = (out / "templates" / "layout" / "intern.twig").read_text(encoding="utf-8")
        self.assertIn("luminare-lockup-compact-{{ _app.theme.is_dark_mode ? 'dark' : 'light' }}.svg", intern)
        base = (out / "templates" / "layout" / "base.twig").read_text(encoding="utf-8")
        self.assertIn("{# lumen-panel:favicon #}{% if _white_label.favicon_url %}", base)
        self.assertIsNone(json.loads((out / "_lumen_build.json").read_text(encoding="utf-8"))["custom"])


class ApplyCustomTest(Env):
    def setUp(self):
        super().setUp()
        self.target = self.tmp / "custom"
        self.options = inst.Options(assets_dir=self.assets, screenshot_fallback=self.shot,
                                    backup_root=self.tmp / "backups", owner="", custom_dir=self.target)
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        self.zip = zip_folder(make_custom(self.tmp / "src"), self.tmp / "lumen-test.zip")

    def test_dry_run_writes_nothing(self):
        before = sorted(p.relative_to(self.tmp) for p in self.tmp.rglob("*"))
        code, out = lines(apply.apply_custom, self.kh, self.zip, list(VARIANTS.values()), options=self.options)
        self.assertEqual(code, 0, out)
        self.assertIn("nothing was written (add --yes)", out)
        self.assertIn("dry run: build and verify passed (Lumen,", out)
        self.assertNotIn("Lumen Dark (theme/lumen-dark)", out)   # not installed: skipped with "all"
        self.assertEqual(before, sorted(p.relative_to(self.tmp) for p in self.tmp.rglob("*")))

    def test_apply_then_check_update_then_reset(self):
        code, out = lines(apply.apply_custom, self.kh, self.zip, list(VARIANTS.values()), options=self.options, yes=True)
        self.assertEqual(code, 0, out)
        self.assertTrue((self.target / "custom" / "logo.svg").is_file())
        self.assertTrue((self.lumen / "assets" / "custom" / "logo.svg").is_file())
        self.assertIn("apply-custom --reset --yes", out)
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        (self.target / "override-follow.css").write_text(CSS + "/* edited */\n", encoding="utf-8")
        code, out = lines(inst.check_update, self.kh, options=self.options)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("customization", out)
        code, out = lines(apply.apply_custom, self.kh, None, [LUMEN], options=self.options, reset=True, yes=True)
        self.assertEqual(code, 0, out)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.lumen / "assets" / "custom").exists())
        self.assertEqual(len(list((self.tmp / "backups" / "custom").iterdir())), 1)
        self.assertIn("apply-custom " + str(self.tmp / "backups" / "custom"), out)

    def test_a_bad_zip_changes_nothing(self):
        bad = self.tmp / "bad.zip"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("lumen.tokens.json", "{}")
        code, out = lines(apply.apply_custom, self.kh, bad, [LUMEN], options=self.options, yes=True)
        self.assertEqual(code, inst.EXIT_USAGE)
        self.assertIn("override-follow.css: missing", out)
        self.assertFalse(self.target.exists())


class CompilerTwinTest(unittest.TestCase):
    """The Python side and tokens/keyhelp.ts agree on the stylesheet kinds; compile.mjs output loads."""

    def test_stylesheet_kinds_match_the_typescript(self):
        ts = (ROOT / "tokens" / "keyhelp.ts").read_text(encoding="utf-8")
        block = ts[ts.index("STYLESHEET_KINDS"):ts.index("};", ts.index("STYLESHEET_KINDS"))]
        kinds = dict(re.findall(r"'([a-z-]+\.css)': '([a-z]+)'", block))
        self.assertEqual(kinds, custom.STYLESHEET_KINDS)
        self.assertEqual(set(kinds), {s for v in VARIANTS.values() for s in v.stylesheets})

    def test_compiled_presets_load(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        major, minor = (int(x) for x in version.lstrip("v").split(".")[:2])
        if (major, minor) < (22, 6):
            self.skipTest(f"node {version} cannot strip types")
        assets = fk.make_assets(Path(self._tmp()) / "assets")
        for name in ("luminare", "graphite", "aurora", "contrast"):
            out = Path(self._tmp()) / name
            subprocess.run([node, "--experimental-strip-types", "--no-warnings", str(ROOT / "tokens" / "compile.mjs"),
                            "--preset", name, "--out", str(out)], check=True, capture_output=True)
            c = custom.load(out, assets)
            self.assertEqual(c.name.lower().replace(" ", ""), {"contrast": "highcontrast"}.get(name, name))

    def _tmp(self) -> str:
        import tempfile
        path = tempfile.mkdtemp(prefix="lumen-compile-")
        self.addCleanup(shutil.rmtree, path, ignore_errors=True)
        return path


if __name__ == "__main__":
    unittest.main()
