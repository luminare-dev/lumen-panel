"""Tests for the lumen_panel generator: patches, build, verify, install, rollback, update checks.

Everything runs against a fake KeyHelp tree in a temporary folder (tests/fakekeyhelp.py); no
test touches a real KeyHelp install.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))
sys.path.insert(0, str(ROOT / "tests"))

import fakekeyhelp as fk  # noqa: E402
from lumen_panel import __version__, cli  # noqa: E402
from lumen_panel import install as inst  # noqa: E402
from lumen_panel.build import BuildError, SourceChangedError, build  # noqa: E402
from lumen_panel.keyhelp import KeyHelpError, tree_sha256  # noqa: E402
from lumen_panel.patches import Patch, PatchError, apply_patches, load_patches, marker  # noqa: E402
from lumen_panel.twigcache import find_theme_entries  # noqa: E402
from lumen_panel.verify import verify  # noqa: E402


def lines(fn, *args, **kwargs):
    out: list[str] = []
    code = fn(*args, out=out.append, **kwargs)
    return code, "\n".join(out)


class Env(unittest.TestCase):
    """A fresh fake KeyHelp, assets folder and backup root per test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lumen-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.kh = fk.make_keyhelp(self.tmp / "keyhelp")
        self.assets = fk.make_assets(self.tmp / "assets")
        self.shot = self.tmp / "shot.png"
        self.shot.write_bytes(fk.tiny_png())
        self.options = inst.Options(assets_dir=self.assets, screenshot_fallback=self.shot,
                                    backup_root=self.tmp / "backups", owner="")
        late = mock.patch.object(inst, "LATE_CACHE_PASS_SECONDS", 0)
        late.start()
        self.addCleanup(late.stop)
        self.lumen = self.kh / "theme" / "lumen"
        self.bulma = self.kh / "theme" / "bulma"
        self.cache = self.kh / "cache" / "twig"

    def build_to(self, out: Path):
        return build(self.kh, out, assets_dir=self.assets, screenshot_fallback=self.shot)

    def bulma_hash(self) -> str:
        return tree_sha256(self.bulma)


class PatchTest(Env):
    def test_patch_set_loads_and_has_markers(self):
        patches = load_patches(fk.PATCHES)
        self.assertGreaterEqual(len(patches), 6)
        self.assertEqual(len({p.id for p in patches}), len(patches))
        for p in patches:
            self.assertTrue(p.marker.startswith("{# lumen-panel:"))

    def test_patches_apply_once_each(self):
        out = self.tmp / "t"
        shutil.copytree(self.bulma / "templates", out)
        patches = load_patches(fk.PATCHES)
        apply_patches(out, patches, {"LUMEN_VERSION": "9.9.9", "LUMEN_ASSET_HASH": "abc"})
        for p in patches:
            text = (out / p.file).read_text(encoding="utf-8")
            self.assertEqual(text.count(p.marker), 1, p.id)
            self.assertNotIn("@@", text)
        base = (out / "layout/base.twig").read_text(encoding="utf-8")
        self.assertLess(base.index("/theme/bulma/assets/css/style.css"), base.index("/theme/lumen/assets/lumen"))
        self.assertLess(base.index("/theme/lumen/assets/lumen"), base.index("{% block page_css %}"))
        self.assertLess(base.index("{% block lumen_island %}"), base.index("</body>"))
        intern = (out / "layout/intern.twig").read_text(encoding="utf-8")
        self.assertTrue(intern.startswith("{% extends 'layout/base.twig' %}"))
        self.assertIn('alt="Luminare Development"', intern)
        self.assertNotIn("keyhelp{{", intern)
        self.assertIn("lumen-island.js?v=abc", intern)

    def test_missing_anchor_fails_loudly_and_writes_nothing(self):
        out = self.tmp / "t"
        shutil.copytree(self.bulma / "templates", out)
        base = out / "layout/base.twig"
        base.write_text(base.read_text(encoding="utf-8").replace("{% block page_css %}{% endblock %}", ""), encoding="utf-8")
        before = {p: p.read_bytes() for p in out.rglob("*.twig")}
        with self.assertRaises(PatchError) as ctx:
            apply_patches(out, load_patches(fk.PATCHES), {"LUMEN_VERSION": "1", "LUMEN_ASSET_HASH": "x"})
        self.assertEqual(len(ctx.exception.failures), 1)
        self.assertIn("base-stylesheet", ctx.exception.failures[0])
        self.assertIn("not found", ctx.exception.failures[0])
        self.assertEqual(before, {p: p.read_bytes() for p in out.rglob("*.twig")})

    def test_duplicate_anchor_and_unknown_token_fail(self):
        out = self.tmp / "t"
        (out / "a").mkdir(parents=True)
        (out / "a/x.twig").write_text("ANCHOR ANCHOR", encoding="utf-8")
        dup = Patch(id="dup", file="a/x.twig", mode="replace", anchor="ANCHOR", text="y", description="d", source="t.json")
        with self.assertRaises(PatchError) as ctx:
            apply_patches(out, [dup], {})
        self.assertIn("found 2 times", ctx.exception.failures[0])
        (out / "a/x.twig").write_text("ANCHOR", encoding="utf-8")
        tok = Patch(id="tok", file="a/x.twig", mode="replace", anchor="ANCHOR", text="@@NOPE@@", description="d", source="t.json")
        with self.assertRaises(PatchError) as ctx:
            apply_patches(out, [tok], {})
        self.assertIn("NOPE", ctx.exception.failures[0])

    def test_bad_patch_files_are_rejected(self):
        bad = self.tmp / "patches"
        bad.mkdir()
        (bad / "1.json").write_text(json.dumps({"id": "x", "file": "../etc/passwd", "mode": "replace",
                                                "anchor": "a", "text": "b", "description": "c"}), encoding="utf-8")
        (bad / "2.json").write_text(json.dumps({"id": "y", "file": "a.twig", "mode": "delete",
                                                "anchor": "a", "text": "b", "description": "c"}), encoding="utf-8")
        with self.assertRaises(PatchError) as ctx:
            load_patches(bad)
        self.assertEqual(len(ctx.exception.failures), 2)


class BuildVerifyTest(Env):
    def test_build_output_and_verify(self):
        before = self.bulma_hash()
        result = self.build_to(self.tmp / "out")
        out = result.out_dir
        settings = json.loads((out / "_settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["name"], "Lumen")
        self.assertEqual(settings["author"], "Luminare Development")
        self.assertEqual(settings["website"], "https://luminare.tech")
        self.assertEqual(settings["version"], __version__)
        self.assertEqual(settings["path_to_templates"], "templates/")
        self.assertIs(settings["has_dark_mode"], True)
        self.assertEqual(settings["lumen_base_version"], "26.1.1")
        self.assertIn("Not affiliated with or endorsed by Keyweb AG", settings["description"])
        self.assertTrue((out / "_screenshot.png").is_file())
        self.assertTrue((out / "assets" / "lumen-island.js").is_file())
        # KeyHelp's own assets are never copied
        self.assertFalse((out / "assets" / "css").exists())
        report = verify(out, self.kh)
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(any(p.startswith("assets (") for p in report.passed))
        self.assertTrue(verify(out).ok)  # against the build record
        self.assertEqual(before, self.bulma_hash(), "the default theme must stay untouched")

    def test_build_refuses_non_empty_output_and_the_default_theme(self):
        (self.tmp / "busy").mkdir()
        (self.tmp / "busy" / "x").write_text("x", encoding="utf-8")
        with self.assertRaises(BuildError):
            self.build_to(self.tmp / "busy")
        with self.assertRaises(BuildError):
            self.build_to(self.bulma / "lumen")

    def test_build_needs_assets(self):
        (self.assets / "lumen-dark.css").unlink()
        with self.assertRaises(BuildError) as ctx:
            self.build_to(self.tmp / "out")
        self.assertIn("lumen-dark.css", str(ctx.exception))

    def test_not_a_keyhelp_root(self):
        with self.assertRaises(KeyHelpError):
            build(self.tmp, self.tmp / "out", assets_dir=self.assets, screenshot_fallback=self.shot)

    def test_verify_finds_problems(self):
        out = self.build_to(self.tmp / "out").out_dir
        (self.bulma / "templates" / "views" / "new.twig").write_text("x", encoding="utf-8")
        (out / "assets" / "brand" / "luminare-lockup-compact-dark.svg").unlink()
        intern = out / "templates" / "layout" / "intern.twig"
        intern.write_text(intern.read_text(encoding="utf-8") + "{% if x %}\n" + marker("intern-logo"), encoding="utf-8")
        errors = "\n".join(verify(out, self.kh).errors)
        self.assertIn("templates/views/new.twig: missing", errors)
        self.assertIn("luminare-lockup-compact-dark.svg does not exist", errors)
        self.assertIn("patch intern-logo present 2 times", errors)
        self.assertIn("if is never closed", errors)


class InstallTest(Env):
    def test_dry_run_changes_nothing(self):
        before = self.bulma_hash()
        code, out = lines(inst.install, self.kh, dry_run=True, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertIn("nothing was written", out)
        self.assertFalse(self.lumen.exists())
        self.assertEqual([p.name for p in (self.kh / "theme").iterdir()], ["bulma"])
        self.assertFalse((self.tmp / "backups").exists())
        self.assertEqual(before, self.bulma_hash())

    def test_install_reinstall_and_rollback(self):
        before = self.bulma_hash()
        code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertTrue(verify(self.lumen, self.kh).ok)
        self.assertIn("select 'Lumen'", out)
        self.assertEqual([p.name for p in (self.kh / "theme").iterdir() if p.name.startswith(".")], [])
        mode = lambda p: p.stat().st_mode & 0o777  # noqa: E731
        self.assertEqual(mode(self.lumen), 0o755)
        self.assertEqual(mode(self.lumen / "_settings.json"), 0o644)
        first_backup_count = len(list((self.tmp / "backups").iterdir()))

        # compiled templates: one of Lumen, one of the default theme
        lumen_entry = fk.compiled_entry(self.cache, "aa" + "1" * 30, f"{self.lumen.resolve()}/templates/layout/base.twig")
        bulma_entry = fk.compiled_entry(self.cache, "bb" + "2" * 30, f"{self.bulma.resolve()}/templates/layout/base.twig")
        self.assertEqual(find_theme_entries(self.cache, self.kh, "lumen"), [lumen_entry])

        # a KeyHelp update, then a reinstall
        fk.set_version(self.kh, "26.2.0")
        later = inst.timestamp() [:-1] + "9Z"  # distinct backup folder name
        with mock.patch.object(inst, "timestamp", return_value=later):
            code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        backup = self.tmp / "backups" / later
        self.assertTrue((backup / "lumen" / "_settings.json").is_file(), out)
        self.assertEqual(json.loads((backup / "lumen" / "_settings.json").read_text())["lumen_base_version"], "26.1.1")
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.2.0")
        self.assertFalse(lumen_entry.exists(), "the Lumen cache entry is moved out")
        self.assertTrue((backup / "twig-cache" / lumen_entry.parent.name / lumen_entry.name).is_file())
        self.assertTrue(bulma_entry.exists(), "default-theme cache entries stay")
        self.assertIn("rollback --keyhelp", (backup / "ROLLBACK.txt").read_text())
        self.assertEqual(len(list((self.tmp / "backups").iterdir())), first_backup_count + 1)

        # rollback restores the saved theme and keeps the backup
        roll = inst.timestamp()[:-1] + "8Z"
        with mock.patch.object(inst, "timestamp", return_value=roll):
            code, out = lines(inst.rollback, self.kh, backup, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.1.1")
        self.assertTrue((backup / "lumen" / "_settings.json").is_file(), "the backup itself is kept")
        self.assertTrue((self.tmp / "backups" / roll / "lumen").is_dir(), "the replaced theme is kept too")
        fk.set_version(self.kh, "26.1.1")
        self.assertEqual(before, self.bulma_hash())

    def test_swap_without_renameat2(self):
        with mock.patch.object(inst, "_renameat2_exchange", return_value=False):
            self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
            later = inst.timestamp()[:-1] + "7Z"
            with mock.patch.object(inst, "timestamp", return_value=later):
                code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertTrue((self.tmp / "backups" / later / "lumen").is_dir())
        self.assertTrue(verify(self.lumen, self.kh).ok)

    def test_renameat2_swaps_atomically(self):
        a, b = self.tmp / "a", self.tmp / "b"
        a.mkdir()
        b.mkdir()
        (a / "x").write_text("a", encoding="utf-8")
        (b / "x").write_text("b", encoding="utf-8")
        if not inst._renameat2_exchange(a, b):
            self.skipTest("renameat2 RENAME_EXCHANGE not available here")
        self.assertEqual((a / "x").read_text(), "b")
        self.assertEqual((b / "x").read_text(), "a")

    def test_failed_patch_installs_nothing(self):
        base = self.bulma / "templates" / "layout" / "base.twig"
        base.write_text(base.read_text(encoding="utf-8").replace("</body>", "</ body>"), encoding="utf-8")
        with self.assertRaises(PatchError) as ctx:
            inst.install(self.kh, options=self.options, out=lambda _l: None)
        self.assertIn("base-island-block", "\n".join(ctx.exception.failures))
        self.assertFalse(self.lumen.exists())
        self.assertEqual([p.name for p in (self.kh / "theme").iterdir()], ["bulma"])
        failed = list((self.tmp / "backups").glob("*/failed-staging"))
        self.assertEqual(len(failed), 1, "the partial build is kept for inspection, not deleted")

    def test_cli_reports_a_failed_patch(self):
        base = self.bulma / "templates" / "layout" / "base.twig"
        base.write_text(base.read_text(encoding="utf-8").replace("</body>", ""), encoding="utf-8")
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["install", "--keyhelp", str(self.kh), "--assets", str(self.assets), "--screenshot",
                             str(self.shot), "--backup-root", str(self.tmp / "backups"), "--owner", ""])
        self.assertEqual(code, 1)
        self.assertIn("base-island-block", err.getvalue())
        self.assertIn("nothing was installed", err.getvalue())


class UpdateTest(Env):
    def test_check_update_and_sync(self):
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], inst.EXIT_NOT_INSTALLED)
        code, out = lines(inst.sync, self.kh, options=self.options)
        self.assertEqual(code, 0)
        self.assertIn("nothing to do", out)
        self.assertFalse(self.lumen.exists())
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        fk.set_version(self.kh, "26.3.0")
        code, out = lines(inst.check_update, self.kh, options=self.options)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("26.3.0", out)
        later = inst.timestamp()[:-1] + "6Z"
        with mock.patch.object(inst, "timestamp", return_value=later):
            self.assertEqual(lines(inst.sync, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        # a template change without a version change is noticed too
        tpl = self.bulma / "templates" / "views" / "extern" / "login.twig"
        tpl.write_text(tpl.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        code, out = lines(inst.check_update, self.kh, options=self.options)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("templates changed", out)

    def test_cli_check_update_exit_codes(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["check-update", "--keyhelp", str(self.kh)]), 3)
            self.assertEqual(cli.main(["check-update", "--keyhelp", str(self.tmp)]), 2)
            self.assertEqual(cli.main(["version"]), 0)


class UninstallTest(Env):
    def test_uninstall_needs_confirmation_and_refuses_while_active(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        code, out = lines(inst.uninstall, self.kh, options=self.options)
        self.assertEqual(code, inst.EXIT_UNCONFIRMED)
        self.assertIn("select the default theme", out)
        self.assertTrue(self.lumen.exists())
        with mock.patch.object(inst, "detect_active", return_value=True):
            code, out = lines(inst.uninstall, self.kh, options=self.options, panel_url="https://panel.example.org/")
        self.assertEqual(code, inst.EXIT_ACTIVE)
        self.assertTrue(self.lumen.exists())
        later = inst.timestamp()[:-1] + "5Z"
        with mock.patch.object(inst, "detect_active", return_value=False), \
                mock.patch.object(inst, "timestamp", return_value=later):
            code, out = lines(inst.uninstall, self.kh, options=self.options, panel_url="https://panel.example.org/")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.lumen.exists())
        self.assertTrue((self.tmp / "backups" / later / "lumen" / "_settings.json").is_file())
        self.assertTrue(self.bulma.is_dir())

    def test_detect_active_reads_the_login_page(self):
        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        page = b'<link rel="stylesheet" href="/theme/lumen/assets/lumen.css?v=1">'
        with mock.patch("urllib.request.urlopen", return_value=Resp(page)):
            self.assertIs(inst.detect_active("https://panel.example.org/"), True)
        bulma_only = b'<link rel="stylesheet" href="/theme/bulma/assets/css/style.css?1">'
        with mock.patch("urllib.request.urlopen", return_value=Resp(bulma_only)):
            self.assertIs(inst.detect_active("https://panel.example.org/"), False)
        # a maintenance or error page shows neither stylesheet: unknown, so uninstall asks for --yes
        with mock.patch("urllib.request.urlopen", return_value=Resp(b"<html>Maintenance</html>")):
            self.assertIsNone(inst.detect_active("https://panel.example.org/"))
        with mock.patch("urllib.request.urlopen", side_effect=OSError("down")):
            self.assertIsNone(inst.detect_active("https://panel.example.org/"))


class SafetyTest(Env):
    """Interrupted runs, parallel runs, half-copied templates and holds (findings F1, F2, F4, F7, F9)."""

    def theme_dirs(self) -> list[str]:
        return sorted(p.name for p in (self.kh / "theme").iterdir())

    def test_a_second_run_is_refused_while_one_holds_the_lock(self):
        with inst.run_lock(self.options):
            with self.assertRaises(inst.BusyError):
                inst.install(self.kh, options=self.options, out=lambda _l: None)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = cli.main(["sync", "--keyhelp", str(self.kh), "--assets", str(self.assets), "--screenshot",
                                 str(self.shot), "--backup-root", str(self.tmp / "backups"), "--owner", ""])
            self.assertEqual(code, inst.EXIT_TEMPFAIL)
            self.assertIn("another lumen-panel run is active", err.getvalue())
        self.assertEqual(self.theme_dirs(), ["bulma"])
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)

    def test_any_exception_during_the_build_moves_staging_out(self):
        for exc in (RuntimeError("boom"), KeyboardInterrupt(), SystemExit(143)):
            with self.subTest(exc=type(exc).__name__):
                with mock.patch.object(inst, "build", side_effect=self._half_build(exc)):
                    with self.assertRaises(type(exc)):
                        inst.install(self.kh, options=self.options, out=lambda _l: None)
                self.assertEqual(self.theme_dirs(), ["bulma"], "no staging folder stays in theme/")
        self.assertEqual(len(list((self.tmp / "backups").glob("*/failed-staging"))), 3)

    def _half_build(self, exc: BaseException):
        def half_build(root, out_dir, **_kw):
            out_dir.mkdir(parents=True)
            (out_dir / "_settings.json").write_text("{}", encoding="utf-8")
            raise exc
        return half_build

    def test_a_failure_during_verify_moves_staging_out(self):
        with mock.patch.object(inst, "verify", side_effect=RuntimeError("verify crashed")):
            with self.assertRaises(RuntimeError):
                inst.install(self.kh, options=self.options, out=lambda _l: None)
        self.assertEqual(self.theme_dirs(), ["bulma"])
        self.assertEqual(len(list((self.tmp / "backups").glob("*/failed-staging/_settings.json"))), 1)

    def test_leftovers_are_moved_to_the_backups_by_the_next_run(self):
        for name in (".lumen-staging-20261021T030000000000Z", ".lumen-previous-20261021T030000000000Z"):
            (self.kh / "theme" / name).mkdir()
            (self.kh / "theme" / name / "_settings.json").write_text("{}", encoding="utf-8")
        code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.theme_dirs(), ["bulma", "lumen"])
        self.assertIn("left by an interrupted run", out)
        self.assertEqual(len(list((self.tmp / "backups").glob("*/stale/.lumen-*/_settings.json"))), 2)

    def test_interrupted_right_after_the_swap(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        old_built = json.loads((self.lumen / "_lumen_build.json").read_text())["built_at"]
        real_move = inst._move

        def stop_at_parking(src, dest):
            if Path(src).name.startswith(inst.PARKING_PREFIX):
                raise KeyboardInterrupt
            return real_move(src, dest)

        fk.set_version(self.kh, "26.2.0")
        with mock.patch.object(inst, "_move", side_effect=stop_at_parking):
            with self.assertRaises(KeyboardInterrupt):
                inst.install(self.kh, options=self.options, out=lambda _l: None)
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.2.0")
        parked = [p for p in (self.kh / "theme").iterdir() if p.name.startswith(inst.PARKING_PREFIX)]
        self.assertEqual(len(parked), 1)
        self.assertFalse((parked[0] / "_settings.json").exists(), "the parked tree is no longer listed as a theme")
        self.assertTrue((parked[0] / "_settings.json.parked").is_file())
        rollback_txt = list((self.tmp / "backups").glob("*/ROLLBACK.txt"))
        self.assertTrue(any(parked[0].name in p.read_text() for p in rollback_txt), "ROLLBACK.txt names the parking path")
        # the next run moves it away; a rollback from there works
        code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.theme_dirs(), ["bulma", "lumen"])
        stale = next((self.tmp / "backups").glob(f"*/stale/{parked[0].name}"))
        fk.set_version(self.kh, "26.1.1")
        code, out = lines(inst.rollback, self.kh, stale, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.lumen / "_lumen_build.json").read_text())["built_at"], old_built)

    def test_interrupted_between_exchange_and_parking(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        real_rename = os.rename

        def stop_after_exchange(src, dest):
            if Path(dest).name.startswith(inst.PARKING_PREFIX):
                raise SystemExit(143)
            return real_rename(src, dest)

        fk.set_version(self.kh, "26.2.0")
        with mock.patch.object(inst.os, "rename", side_effect=stop_after_exchange):
            with self.assertRaises(SystemExit):
                inst.install(self.kh, options=self.options, out=lambda _l: None)
        staged = [p for p in (self.kh / "theme").iterdir() if p.name.startswith(inst.STAGING_PREFIX)]
        if not staged:
            self.skipTest("renameat2 RENAME_EXCHANGE not available here (fallback path)")
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.2.0")
        self.assertFalse((staged[0] / "_settings.json").exists())
        self.assertTrue(any(staged[0].name in p.read_text() for p in (self.tmp / "backups").glob("*/ROLLBACK.txt")))
        self.assertEqual(list((self.tmp / "backups").glob("*/failed-staging")), [],
                         "the previous theme is not mistaken for a failed build")

    def test_a_failure_after_the_swap_is_exit_1_and_says_the_theme_is_installed(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.hold, self.options)[0], 0)
        fk.set_version(self.kh, "26.2.0")
        err = io.StringIO()
        with mock.patch.object(inst, "move_cache_entries", side_effect=OSError("cache vanished")), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["install", "--keyhelp", str(self.kh), "--assets", str(self.assets), "--screenshot",
                             str(self.shot), "--backup-root", str(self.tmp / "backups"), "--owner", ""])
        self.assertEqual(code, 1)
        self.assertIn("the new theme is installed", err.getvalue())
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.2.0")
        self.assertTrue(list((self.tmp / "backups").glob("*/lumen/_settings.json")), "the old theme still reached the backups")
        self.assertTrue(list((self.tmp / "backups").glob("*/ROLLBACK.txt")))
        self.assertFalse((self.tmp / "backups" / "HOLD").exists(), "the swap succeeded, so the hold is released")

    def test_cache_entries_that_vanish_are_skipped(self):
        entry = fk.compiled_entry(self.cache, "ab" + "1" * 30, f"{self.lumen.resolve()}/templates/x.twig")
        with mock.patch.object(inst, "find_theme_entries", return_value=[entry, self.cache / "ab" / "gone.php"]):
            moved = inst.move_cache_entries(inst.KeyHelpTree(self.kh), self.tmp / "dest")
        self.assertEqual(len(moved), 1)

    def test_timestamps_have_microseconds(self):
        self.assertRegex(inst.timestamp(), r"^\d{8}T\d{12}Z$")


class ContentTest(Env):
    def test_a_truncated_template_fails_verify(self):
        out = self.build_to(self.tmp / "out").out_dir
        self.assertTrue(verify(out, self.kh).ok)
        login = out / "templates" / "views" / "extern" / "login.twig"
        login.write_bytes(b"")
        for report in (verify(out, self.kh), verify(out)):
            self.assertFalse(report.ok)
            self.assertIn("views/extern/login.twig: content differs", "\n".join(report.errors))

    def test_a_patched_template_must_reproduce_exactly(self):
        out = self.build_to(self.tmp / "out").out_dir
        base = out / "templates" / "layout" / "base.twig"
        base.write_bytes(base.read_bytes().replace(b"<title>", b"<title>x"))
        errors = "\n".join(verify(out, self.kh).errors)
        self.assertIn("layout/base.twig: is not the live default theme's file with the recorded patches", errors)

    def test_a_change_of_the_default_theme_during_the_build_stops_it(self):
        real = inst.build.__globals__["_copy_exact"]

        def copy_then_update(src, dest, files):
            hashes = real(src, dest, files)
            tpl = self.bulma / "templates" / "views" / "extern" / "login.twig"
            tpl.write_text(tpl.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            return hashes

        with mock.patch.dict(inst.build.__globals__, {"_copy_exact": copy_then_update}):
            with self.assertRaises(SourceChangedError):
                inst.install(self.kh, options=self.options, out=lambda _l: None)
        self.assertEqual(self.theme_dirs(), ["bulma"])

    def theme_dirs(self) -> list[str]:
        return sorted(p.name for p in (self.kh / "theme").iterdir())

    def test_path_order_with_dashes_is_not_taken_for_a_change(self):
        """list_files sorts Path objects ("a/x" before "a-b/x"), not strings; the copy check must agree."""
        for rel in ("views/a-b/x.twig", "views/a/x.twig", "views/a.b/y.twig"):
            path = self.bulma / "templates" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{# fixture #}\n", encoding="utf-8")
        out = self.build_to(self.tmp / "out").out_dir
        self.assertTrue(verify(out, self.kh).ok)

    def test_a_renamed_variable_stops_the_patch(self):
        base = self.bulma / "templates" / "layout" / "base.twig"
        base.write_text(base.read_text(encoding="utf-8").replace("_app.text_direction", "_app.direction"), encoding="utf-8")
        with self.assertRaises(PatchError) as ctx:
            self.build_to(self.tmp / "out")
        self.assertIn("_app.text_direction no longer used in layout/base.twig", "\n".join(ctx.exception.failures))

    def test_line_endings_are_kept(self):
        base = self.bulma / "templates" / "layout" / "base.twig"
        base.write_bytes(base.read_bytes().replace(b"\n", b"\r\n"))
        out = self.build_to(self.tmp / "out").out_dir
        self.assertNotIn(b"\r\r", (out / "templates" / "layout" / "base.twig").read_bytes())
        self.assertEqual((out / "templates" / "layout" / "base.twig").read_bytes().count(b"\r\n"),
                         base.read_bytes().count(b"\r\n"), "every CRLF of the source is kept")
        self.assertTrue(verify(out, self.kh).ok)

    def test_stray_asset_files_stop_the_build(self):
        (self.assets / "lumen-island.js.map").write_text("{}", encoding="utf-8")
        with self.assertRaises(BuildError) as ctx:
            self.build_to(self.tmp / "out")
        self.assertIn("lumen-island.js.map", str(ctx.exception))


class HoldTest(Env):
    def test_rollback_holds_and_install_releases(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        first = sorted((self.tmp / "backups").glob("*/ROLLBACK.txt"))[0].parent
        fk.set_version(self.kh, "26.1.3")
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        second = sorted(p.parent for p in (self.tmp / "backups").glob("*/lumen"))[-1]
        self.assertNotEqual(first, second)
        fk.set_version(self.kh, "26.1.4")
        code, out = lines(inst.rollback, self.kh, second, options=self.options)
        self.assertEqual(code, 0, out)
        hold = json.loads((self.tmp / "backups" / "HOLD").read_text())
        self.assertEqual(hold["by"], "rollback")
        self.assertEqual(hold["from"], str(second))
        code, out = lines(inst.check_update, self.kh, options=self.options)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("after a rollback", out)
        code, out = lines(inst.sync, self.kh, options=self.options)
        self.assertEqual(code, 0)
        self.assertIn("run install to resume", out)
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.1.1",
                         "sync keeps the rolled-back build")
        code, out = lines(inst.install, self.kh, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertFalse((self.tmp / "backups" / "HOLD").exists())
        self.assertEqual(json.loads((self.lumen / "_settings.json").read_text())["lumen_base_version"], "26.1.4")

    def test_hold_and_release_commands(self):
        root = str(self.tmp / "backups")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["hold", "--backup-root", root]), 0)
            self.assertTrue((self.tmp / "backups" / "HOLD").is_file())
            self.assertEqual(cli.main(["release", "--backup-root", root]), 0)
            self.assertFalse((self.tmp / "backups" / "HOLD").exists())
            self.assertEqual(cli.main(["release", "--backup-root", root]), 0)

    def test_check_update_sees_new_assets_and_patches(self):
        self.assertEqual(lines(inst.install, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        css = self.assets / "lumen.css"
        css.write_text(css.read_text(encoding="utf-8") + "a{}\n", encoding="utf-8")
        code, out = lines(inst.check_update, self.kh, options=self.options)
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("built assets changed", out)
        self.assertEqual(lines(inst.sync, self.kh, options=self.options)[0], 0)
        self.assertEqual(lines(inst.check_update, self.kh, options=self.options)[0], 0)
        patches = self.tmp / "patches"
        shutil.copytree(fk.PATCHES, patches)
        first = sorted(patches.glob("*.json"))[0]
        first.write_text(first.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        code, out = lines(inst.check_update, self.kh, options=inst.Options(
            patches_dir=patches, assets_dir=self.assets, backup_root=self.tmp / "backups"))
        self.assertEqual(code, inst.EXIT_REBUILD_NEEDED)
        self.assertIn("patch set", out)


class DryRunTest(Env):
    def test_dry_run_checks_owner_and_folders(self):
        code, out = lines(inst.install, self.kh, dry_run=True, options=self.options)
        self.assertEqual(code, 0, out)
        self.assertIn("is writable", out)
        self.assertIn("can be created", out)
        bad = inst.Options(assets_dir=self.assets, screenshot_fallback=self.shot,
                           backup_root=self.tmp / "backups", owner="no-such-user-lumen:no-such-group")
        code, out = lines(inst.install, self.kh, dry_run=True, options=bad)
        self.assertEqual(code, inst.EXIT_FAILED)
        self.assertIn("unknown user or group", out)
        self.assertFalse((self.tmp / "backups").exists(), "a dry run writes nothing")


class CacheTest(Env):
    def test_only_lumen_entries_are_selected(self):
        lumen_abs = fk.compiled_entry(self.cache, "0a" + "3" * 30, f"{self.lumen.resolve()}/templates/x.twig")
        lumen_rel = fk.compiled_entry(self.cache, "0b" + "4" * 30, "theme/lumen/templates/y.twig")
        fk.compiled_entry(self.cache, "0c" + "5" * 30, f"{self.bulma.resolve()}/templates/x.twig")
        fk.compiled_entry(self.cache, "0d" + "6" * 30, f"{self.kh.resolve()}/theme/lumen-old/templates/x.twig")
        (self.cache / "0e").mkdir()
        (self.cache / "0e" / ("7" * 32 + ".php")).write_text("<?php // no source recorded", encoding="utf-8")
        (self.cache / "notes.txt").write_text("not a cache entry", encoding="utf-8")
        found = find_theme_entries(self.cache, self.kh, "lumen")
        self.assertEqual(sorted(found), sorted([lumen_abs, lumen_rel]))

    def test_missing_cache_folder(self):
        shutil.rmtree(self.cache)
        self.assertEqual(find_theme_entries(self.cache, self.kh, "lumen"), [])


class SettingsFileTest(unittest.TestCase):
    def test_settings_are_stable_json(self):
        from lumen_panel.build import settings_document

        doc = settings_document("26.1.1")
        self.assertEqual(list(doc)[:7], ["name", "description", "author", "version", "website",
                                         "path_to_templates", "has_dark_mode"])
        self.assertNotIn("KeyHelp", doc["name"])
        self.assertEqual(hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest(),
                         hashlib.sha256(json.dumps(settings_document("26.1.1"), sort_keys=True).encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
