"""Command line: python3 -m lumen_panel <command> [--variant lumen|lumen-dark] ...

    build         --keyhelp ROOT --out DIR       build the theme folder (writes only DIR)
    verify        DIR [--keyhelp ROOT]           check a built or installed theme folder
    install       --keyhelp ROOT [--dry-run]     build, verify and swap in theme/<variant> (backup first)
    rollback      --keyhelp ROOT --from BACKUP   put a saved theme/<variant> back (the backup is kept)
    check-update  --keyhelp ROOT                 0 current, 10 rebuild needed, 3 not installed
    sync          --keyhelp ROOT                 check-update, then install when a rebuild is needed
    uninstall     --keyhelp ROOT [--panel-url URL] [--yes]   move theme/<variant> to the backups
    hold                                         stop sync from rebuilding (also set by rollback)
    release                                      let sync rebuild again
    version                                      print the generator version

--variant picks the theme: lumen (theme/lumen, "Lumen", the default) or lumen-dark
(theme/lumen-dark, "Lumen Dark", always dark). check-update and sync also take --variant all,
which checks or syncs every installed variant, one after the other; hold and release take it too
and hold or release every variant. verify reads the variant from the build record unless
--variant names the one expected.

Exit codes: 0 ok, 1 failed, 2 usage or input error, 3 not installed, 4 the theme is still active,
5 not confirmed, 10 rebuild needed, 75 busy or the default theme changed meanwhile (retry later).
"""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from . import __version__, variants
from .build import DEFAULT_ASSETS, DEFAULT_PATCHES, BuildError, SourceChangedError, build
from .install import (DEFAULT_BACKUP_ROOT, DEFAULT_OWNER, EXIT_FAILED, EXIT_NOT_INSTALLED, EXIT_OK,
                      EXIT_REBUILD_NEEDED, EXIT_TEMPFAIL, EXIT_USAGE, BusyError, InstallError, Options, PostSwapError,
                      check_update, hold, install, installed, release, rollback, sync, uninstall)
from .keyhelp import KeyHelpError, KeyHelpTree
from .patches import PatchError
from .verify import verify

ALL = "all"


def _variant_option(p: argparse.ArgumentParser, *, allow_all: bool = False, default: str | None = "lumen") -> None:
    choices = [*variants.VARIANTS, *([ALL] if allow_all else [])]
    text = "the theme: lumen (theme/lumen) or lumen-dark (theme/lumen-dark, always dark)"
    if allow_all:
        text += "; all: every variant (sync and check-update: every installed one)"
    if default is None:
        text = "the variant the folder must hold (default: the one its build record names)"
    else:
        text += " (default: %(default)s)"
    p.add_argument("--variant", choices=choices, default=default, help=text)


def _common(p: argparse.ArgumentParser, *, keyhelp: bool = True, deploy: bool = False) -> None:
    if keyhelp:
        p.add_argument("--keyhelp", type=Path, required=True,
                       help="KeyHelp web root, for example /home/keyhelp/www/keyhelp (read-only except the theme's "
                            "own folders below theme/)")
    p.add_argument("--patches", type=Path, default=DEFAULT_PATCHES, help="patch folder (default: %(default)s)")
    p.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="built assets (default: %(default)s)")
    p.add_argument("--screenshot", type=Path, default=None,
                   help="pre-rendered preview used without PyMuPDF (default: the variant's file in assets/brand/)")
    if deploy:
        p.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT,
                       help="where replaced themes and cache entries go; Lumen Dark uses its lumen-dark/ subfolder "
                            "(default: %(default)s)")
        p.add_argument("--owner", default=DEFAULT_OWNER,
                       help="user:group of the installed files, '' to keep (default: %(default)s)")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python3 -m lumen_panel", description=(__doc__ or "").splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build the theme folder")
    _common(b)
    _variant_option(b)
    b.add_argument("--out", type=Path, required=True, help="output folder (must not exist or be empty)")
    v = sub.add_parser("verify", help="check a theme folder")
    v.add_argument("dir", type=Path)
    v.add_argument("--keyhelp", type=Path, help="compare with the live default theme instead of the build record")
    _variant_option(v, default=None)
    i = sub.add_parser("install", help="build, verify and swap in theme/<variant>")
    _common(i, deploy=True)
    _variant_option(i)
    i.add_argument("--dry-run", action="store_true", help="build and verify in a temporary folder; change nothing")
    r = sub.add_parser("rollback", help="restore a saved theme/<variant>")
    _common(r, deploy=True)
    _variant_option(r)
    r.add_argument("--from", dest="backup", type=Path, required=True,
                   help="a backup folder <backups>/<timestamp> of the same variant")
    c = sub.add_parser("check-update", help="exit 10 when a rebuild is needed")
    c.add_argument("--keyhelp", type=Path, required=True)
    c.add_argument("--patches", type=Path, default=DEFAULT_PATCHES, help="patch folder to compare (default: %(default)s)")
    c.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="built assets to compare (default: %(default)s)")
    c.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT,
                   help="where a hold is recorded (default: %(default)s)")
    _variant_option(c, allow_all=True)
    s = sub.add_parser("sync", help="check-update, then install when needed")
    _common(s, deploy=True)
    _variant_option(s, allow_all=True)
    u = sub.add_parser("uninstall", help="move theme/<variant> to the backups")
    _common(u, deploy=True)
    _variant_option(u)
    u.add_argument("--panel-url", help="login page of this panel; refuse while it still loads the theme")
    u.add_argument("--insecure", action="store_true", help="do not verify the panel's TLS certificate")
    u.add_argument("--yes", action="store_true", help="another theme is selected; go ahead without --panel-url")
    for name, text in (("hold", "stop sync from rebuilding until release or install"),
                       ("release", "let sync rebuild again after a hold or rollback")):
        h = sub.add_parser(name, help=text)
        h.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT,
                       help="where the hold is recorded (default: %(default)s)")
        _variant_option(h, allow_all=True)
    sub.add_parser("version", help="print the version")
    return p


def _options(args: argparse.Namespace, variant: variants.Variant | None = None) -> Options:
    name = getattr(args, "variant", None)
    return Options(patches_dir=getattr(args, "patches", DEFAULT_PATCHES),
                   assets_dir=getattr(args, "assets", DEFAULT_ASSETS),
                   screenshot_fallback=getattr(args, "screenshot", None),
                   backup_root=getattr(args, "backup_root", DEFAULT_BACKUP_ROOT),
                   owner=getattr(args, "owner", DEFAULT_OWNER),
                   variant=variant or variants.get(name if name and name != ALL else variants.DEFAULT_VARIANT.name))


def _terminate(signum: int, _frame: object) -> None:
    # systemd stops a unit with SIGTERM (timeout, shutdown). Raising lets the cleanup code run:
    # an unfinished build is moved out of theme/ instead of being left there.
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        previous = signal.signal(signal.SIGTERM, _terminate)
    except ValueError:  # not the main thread (embedded use): keep the default handling
        previous = None
    try:
        if getattr(args, "variant", None) == ALL:
            if args.command in ("hold", "release"):
                return _run_each(args)
            return _run_all(args)
        return _run(args)
    finally:
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)


def _run_each(args: argparse.Namespace) -> int:
    """hold or release every variant, installed or not (they need no KeyHelp root); the first code
    that is not 0 wins. A hold of a variant that is not installed changes nothing until it is."""
    codes: list[int] = []
    for v in variants.VARIANTS.values():
        print(f"== {v.display_name} (theme/{v.dir_name})")
        codes.append(_run(args, v))
    return next((c for c in codes if c != EXIT_OK), EXIT_OK)


def _run_all(args: argparse.Namespace) -> int:
    """check-update or sync for every variant, one after the other; one variant's failure does not
    stop the others. sync skips a variant that is not installed (no lock, no backup folder).

    sync's exit code: 75 wins over 1 and 2, so that a variant that was busy or saw the default theme
    still changing is retried (the unit restarts on 75 only); the other variant's failure then shows
    on the last retry, when nothing is busy any more. A retry is harmless: a failing build writes
    nothing."""
    if getattr(args, "screenshot", None) is not None:
        print("error: --screenshot needs a single --variant (each theme has its own preview)", file=sys.stderr)
        return EXIT_USAGE
    try:
        tree = KeyHelpTree(args.keyhelp).validate()
    except KeyHelpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    codes: list[int] = []
    for v in variants.VARIANTS.values():
        print(f"== {v.display_name} (theme/{v.dir_name})")
        if args.command == "sync" and not installed(tree, v):
            print(f"sync: {v.display_name} is not installed; nothing to do")
            codes.append(EXIT_NOT_INSTALLED)
            continue
        codes.append(_run(args, v))
    if args.command == "check-update":
        if EXIT_REBUILD_NEEDED in codes:
            return EXIT_REBUILD_NEEDED
        rest = [c for c in codes if c not in (EXIT_OK, EXIT_NOT_INSTALLED)]
        if rest:
            return rest[0]
        return EXIT_NOT_INSTALLED if all(c == EXIT_NOT_INSTALLED for c in codes) else EXIT_OK
    for severe in (EXIT_TEMPFAIL, EXIT_FAILED, EXIT_USAGE):
        if severe in codes:
            return severe
    return next((c for c in codes if c not in (EXIT_OK, EXIT_NOT_INSTALLED)), EXIT_OK)


def _run(args: argparse.Namespace, variant: variants.Variant | None = None) -> int:
    try:
        if args.command == "version":
            print(__version__)
            return 0
        if args.command == "build":
            v = variants.get(args.variant)
            result = build(args.keyhelp, args.out, variant=v, patches_dir=args.patches, assets_dir=args.assets,
                           screenshot_fallback=args.screenshot)
            print(f"built {result.out_dir} ({v.display_name}) from default theme {result.base_version}: "
                  f"{len(result.patches)} patches, assets {result.asset_hash}, screenshot {result.screenshot}")
            report = verify(result.out_dir, args.keyhelp, variant=v)
            for e in report.errors:
                print(f"error: {e}")
            print("verify: " + ("ok: " + ", ".join(report.passed) if report.ok else "FAILED"))
            return 0 if report.ok else EXIT_FAILED
        if args.command == "verify":
            report = verify(args.dir, args.keyhelp, variant=variants.get(args.variant) if args.variant else None)
            for e in report.errors:
                print(f"error: {e}")
            for passed in report.passed:
                print(f"ok: {passed}")
            return 0 if report.ok else EXIT_FAILED
        options = _options(args, variant)
        if args.command == "install":
            return install(args.keyhelp, dry_run=args.dry_run, options=options)
        if args.command == "rollback":
            return rollback(args.keyhelp, args.backup, options=options)
        if args.command == "check-update":
            return check_update(args.keyhelp, options=options)
        if args.command == "sync":
            return sync(args.keyhelp, options=options)
        if args.command == "uninstall":
            return uninstall(args.keyhelp, options=options, panel_url=args.panel_url,
                             insecure=args.insecure, confirmed=args.yes)
        if args.command == "hold":
            return hold(options)
        if args.command == "release":
            return release(options)
    except (BusyError, SourceChangedError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TEMPFAIL
    except PostSwapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAILED
    except PatchError as exc:
        print("error: the patch set does not fit this KeyHelp version; nothing was installed", file=sys.stderr)
        for f in exc.failures:
            print(f"  {f}", file=sys.stderr)
        return EXIT_FAILED
    except (BuildError, InstallError, KeyHelpError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    return EXIT_USAGE
