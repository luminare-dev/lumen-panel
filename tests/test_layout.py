"""KeyHelp's two default-theme layouts: theme/default (26.2 and later) and theme/bulma (before).

The fake KeyHelp of tests/fakekeyhelp.py writes either one. The generator must read the one the
install has, point {{ _app.theme.url }} at it, and refuse builds made for the other one.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))
sys.path.insert(0, str(ROOT / "tests"))

import fakekeyhelp as fk  # noqa: E402
import test_generator as tg  # noqa: E402
import test_variants as tv  # noqa: E402
from lumen_panel import custom  # noqa: E402
from lumen_panel import install as inst  # noqa: E402
from lumen_panel.build import BuildError, build  # noqa: E402
from lumen_panel.keyhelp import KeyHelpError, KeyHelpTree, layout_for_version, parse_version  # noqa: E402
from lumen_panel.patches import PatchError, load_patches  # noqa: E402
from lumen_panel.variants import LUMEN, LUMEN_DARK  # noqa: E402
from lumen_panel.verify import verify  # noqa: E402

lines = tg.lines


def upgrade_to_26_2(kh: Path) -> None:
    """What the KeyHelp 26.2 update did: theme/bulma gone, theme/default with the new templates."""
    tmp = Path(tempfile.mkdtemp(prefix="lumen-upgrade-"))
    try:
        fk.make_keyhelp(tmp / "kh", layout="default")
        shutil.rmtree(kh / "theme" / "bulma")
        shutil.move(str(tmp / "kh" / "theme" / "default"), kh / "theme" / "default")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class VersionTest(tg.unittest.TestCase):
    def test_versions_and_layouts(self):
        self.assertEqual(parse_version("26.2"), (26, 2))
        self.assertEqual(parse_version("26.1.1"), (26, 1, 1))
        self.assertIsNone(parse_version("dev"))
        self.assertEqual(layout_for_version("26.2"), "default")
        self.assertEqual(layout_for_version("26.2.0"), "default")
        self.assertEqual(layout_for_version("27.0"), "default")
        self.assertEqual(layout_for_version("26.1.9"), "bulma")
        self.assertEqual(layout_for_version("25.0"), "bulma")


class TreeTest(tg.Env):
    def test_the_install_layout_is_detected(self):
        tree = KeyHelpTree(self.kh).validate()
        self.assertEqual(tree.layout, "default")
        self.assertEqual(tree.base_url, "/theme/default")
        self.assertEqual(tree.describe(), "KeyHelp 26.2, default theme in theme/default")

    def test_a_folder_that_does_not_fit_the_version_is_refused(self):
        fk.set_version(self.kh, "26.1.1")
        with self.assertRaises(KeyHelpError) as ctx:
            KeyHelpTree(self.kh).validate()
        self.assertIn("KeyHelp 26.1.1 keeps its default theme in theme/bulma", str(ctx.exception))
        self.assertIn("this install has theme/default", str(ctx.exception))
        with self.assertRaises(KeyHelpError):
            inst.install(self.kh, dry_run=True, options=self.options, out=lambda _: None)

    def test_no_default_theme_names_both_folders(self):
        shutil.rmtree(self.base)
        with self.assertRaises(KeyHelpError) as ctx:
            KeyHelpTree(self.kh).validate()
        self.assertIn("theme/default/_settings.json or theme/bulma/_settings.json", str(ctx.exception))

    def test_an_old_bulma_folder_next_to_default_is_ignored(self):
        old = Path(tempfile.mkdtemp(prefix="lumen-old-"))
        self.addCleanup(shutil.rmtree, old, ignore_errors=True)
        fk.make_keyhelp(old / "kh", layout="bulma")
        shutil.move(str(old / "kh" / "theme" / "bulma"), self.kh / "theme" / "bulma")
        self.assertEqual(KeyHelpTree(self.kh).validate().layout, "default")


class RebaseTest(tg.Env):
    def test_theme_urls_point_at_the_default_theme(self):
        for variant in (LUMEN, LUMEN_DARK):
            out = build(self.kh, self.tmp / variant.dir_name, variant=variant, assets_dir=self.assets,
                        screenshot_fallback=self.shot).out_dir
            manifest = json.loads((out / "_lumen_build.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["base_theme"], "default")
            self.assertEqual(manifest["base_url"], "/theme/default")
            self.assertIn("views/extern/login.twig", manifest["rebased_files"])
            for twig in (out / "templates").rglob("*.twig"):
                self.assertNotIn("_app.theme.url", twig.read_text(encoding="utf-8"), twig)
            login = (out / "templates" / "views" / "extern" / "login.twig").read_text(encoding="utf-8")
            self.assertIn('src="/theme/default/assets/js/login.js"', login)
            base = (out / "templates" / "layout" / "base.twig").read_text(encoding="utf-8")
            self.assertIn('href="/theme/default/assets/css/style', base)
            self.assertIn('src="/theme/default/assets/js/main.js"', base)
            report = verify(out, self.kh)
            self.assertTrue(report.ok, report.errors)
            self.assertIn("layout (theme/default)", report.passed)
            self.assertTrue(verify(out).ok)

    def test_an_unknown_use_of_the_theme_url_stops_the_build(self):
        view = self.base / "templates" / "views" / "intern" / "admin" / "dashboard.twig"
        view.write_text(view.read_text(encoding="utf-8") + "{{ _app.theme.url ~ '/x.js' }}\n", encoding="utf-8")
        with self.assertRaises(BuildError) as ctx:
            self.build_to(self.tmp / "out")
        self.assertIn("views/intern/admin/dashboard.twig", str(ctx.exception))

    def test_verify_catches_a_template_that_still_uses_the_theme_url(self):
        out = self.build_to(self.tmp / "out").out_dir
        login = out / "templates" / "views" / "extern" / "login.twig"
        login.write_text(login.read_text(encoding="utf-8").replace("/theme/default", "{{ _app.theme.url }}"),
                         encoding="utf-8")
        errors = "\n".join(verify(out).errors)
        self.assertIn("templates/views/extern/login.twig: still uses _app.theme.url", errors)

    def test_an_empty_logo_brings_back_keyhelps_from_the_default_theme(self):
        html = custom.logo_html(LUMEN, "header", {**custom.DEFAULT_BRANDING, "headerLight": "", "headerDark": ""},
                                "lumen", "x", "/theme/default")
        self.assertTrue(html.startswith('<img src="/theme/default/assets/img/'), html)
        self.assertIn("/theme/bulma/assets/img/", custom.keyhelp_logo("/theme/bulma"))

    def test_detect_active_knows_both_folders(self):
        class Resp(tg.io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        for base in ("default", "bulma"):
            page = f'<link rel="stylesheet" href="/theme/{base}/assets/css/style.css?1">'.encode()
            with mock.patch("urllib.request.urlopen", return_value=Resp(page)):
                self.assertIs(inst.detect_active("https://panel.invalid/"), False)


class AnchorsTest(tg.unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lumen-anchors-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, item: dict) -> Path:
        (self.tmp / "1.json").write_text(json.dumps({"id": "xx", "file": "a.twig", "mode": "replace", "text": "b",
                                                     "description": "c", **item}), encoding="utf-8")
        return self.tmp

    def test_each_layout_gets_its_anchor(self):
        folder = self.write({"anchors": {"default": "NEW", "bulma": "OLD"}})
        self.assertEqual(load_patches(folder, layout="default")[0].anchor, "NEW")
        self.assertEqual(load_patches(folder, layout="bulma")[0].anchor, "OLD")

    def test_bad_anchors_are_rejected(self):
        for item, needle in (({"anchor": "a", "anchors": {"default": "b"}}, "either 'anchor' or 'anchors'"),
                             ({"anchors": {"default": "b"}}, "no anchor for the theme/bulma layout"),
                             ({"anchors": {"other": "b"}}, "must map layouts"),
                             ({"anchors": {"bulma": ""}}, "must map layouts")):
            with self.subTest(item=item), self.assertRaises(PatchError) as ctx:
                load_patches(self.write(item), layout="bulma")
            self.assertIn(needle, "\n".join(ctx.exception.failures))

    def test_the_shipped_patch_sets_cover_both_layouts(self):
        for layout in fk.LAYOUTS:
            for variant in (LUMEN, LUMEN_DARK):
                self.assertTrue(load_patches(fk.PATCHES, variant.patch_overlay, layout))


class UpgradeTest(tg.Env):
    """A Lumen built on KeyHelp 26.1 (theme/bulma), then KeyHelp updates itself to 26.2."""

    LAYOUT = "bulma"

    def test_check_update_rollback_and_reinstall_after_the_26_2_update(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        later = inst.timestamp()[:-1] + "9Z"
        with mock.patch.object(inst, "timestamp", return_value=later):
            self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        saved = self.tmp / "backups" / later   # holds the first (bulma) build
        upgrade_to_26_2(self.kh)

        code, out = lines(inst.check_update, self.kh, options=self.options)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("built for theme/bulma (KeyHelp before 26.2)", out)
        self.assertIn("KeyHelp 26.2, default theme in theme/default", out)

        errors = "\n".join(verify(self.lumen, self.kh).errors)
        self.assertIn("built for theme/bulma", errors)
        self.assertIn("loads files from theme/bulma/", errors)

        with self.assertRaises(inst.InstallError) as ctx:
            inst.rollback(self.kh, saved, options=self.options, out=lambda _: None)
        self.assertIn("refused", str(ctx.exception))
        self.assertIn("Default Theme", str(ctx.exception))

        code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertIn("panel: KeyHelp 26.2, default theme in theme/default", out)
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        manifest = json.loads((self.lumen / "_lumen_build.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["base_theme"], "default")
        self.assertTrue(verify(self.lumen, self.kh).ok)


# The generator and variant tests once more on the layout before KeyHelp 26.2 (theme/bulma).
class LegacyPatchTest(tg.PatchTest):
    LAYOUT = "bulma"


class LegacyBuildVerifyTest(tg.BuildVerifyTest):
    LAYOUT = "bulma"


class LegacyInstallTest(tg.InstallTest):
    LAYOUT = "bulma"


class LegacyUpdateTest(tg.UpdateTest):
    LAYOUT = "bulma"


class LegacyContentTest(tg.ContentTest):
    LAYOUT = "bulma"


class LegacyProBoundaryTest(tv.ProBoundaryTest):
    LAYOUT = "bulma"


class LegacyVariantBuildTest(tv.BuildTest):
    LAYOUT = "bulma"


if __name__ == "__main__":
    tg.unittest.main()
