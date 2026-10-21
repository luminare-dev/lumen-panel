"""Command line: python3 -m lumen_panel <command> ...

    build         --keyhelp ROOT --out DIR       build the theme folder (writes only DIR)
    verify        DIR [--keyhelp ROOT]           check a built or installed theme folder
    install       --keyhelp ROOT [--dry-run]     build, verify and swap in theme/lumen (backup first)
    rollback      --keyhelp ROOT --from BACKUP   put a saved theme/lumen back (the backup is kept)
    check-update  --keyhelp ROOT                 0 current, 10 rebuild needed, 3 not installed
    sync          --keyhelp ROOT                 check-update, then install when a rebuild is needed
    uninstall     --keyhelp ROOT [--panel-url URL] [--yes]   move theme/lumen to the backups
    hold                                         stop sync from rebuilding (also set by rollback)
    release                                      let sync rebuild again
    version                                      print the generator version

Exit codes: 0 ok, 1 failed, 2 usage or input error, 3 not installed, 4 Lumen still active,
5 not confirmed, 10 rebuild needed, 75 busy or the default theme changed meanwhile (retry later).
"""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from . import __version__
from .build import DEFAULT_ASSETS, DEFAULT_PATCHES, DEFAULT_SCREENSHOT, BuildError, SourceChangedError, build
from .install import (DEFAULT_BACKUP_ROOT, DEFAULT_OWNER, EXIT_FAILED, EXIT_TEMPFAIL, EXIT_USAGE, BusyError,
                      InstallError, Options, PostSwapError, check_update, hold, install, release, rollback, sync,
                      uninstall)
from .keyhelp import KeyHelpError
from .patches import PatchError
from .verify import verify


def _common(p: argparse.ArgumentParser, *, keyhelp: bool = True, deploy: bool = False) -> None:
    if keyhelp:
        p.add_argument("--keyhelp", type=Path, required=True,
                       help="KeyHelp web root, for example /home/keyhelp/www/keyhelp (read-only except theme/lumen)")
    p.add_argument("--patches", type=Path, default=DEFAULT_PATCHES, help="patch folder (default: %(default)s)")
    p.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="built assets (default: %(default)s)")
    p.add_argument("--screenshot", type=Path, default=DEFAULT_SCREENSHOT,
                   help="pre-rendered preview used without PyMuPDF (default: %(default)s)")
    if deploy:
        p.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT,
                       help="where replaced themes and cache entries go (default: %(default)s)")
        p.add_argument("--owner", default=DEFAULT_OWNER,
                       help="user:group of the installed files, '' to keep (default: %(default)s)")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python3 -m lumen_panel", description=(__doc__ or "").splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build the theme folder")
    _common(b)
    b.add_argument("--out", type=Path, required=True, help="output folder (must not exist or be empty)")
    v = sub.add_parser("verify", help="check a theme folder")
    v.add_argument("dir", type=Path)
    v.add_argument("--keyhelp", type=Path, help="compare with the live default theme instead of the build record")
    i = sub.add_parser("install", help="build, verify and swap in theme/lumen")
    _common(i, deploy=True)
    i.add_argument("--dry-run", action="store_true", help="build and verify in a temporary folder; change nothing")
    r = sub.add_parser("rollback", help="restore a saved theme/lumen")
    _common(r, deploy=True)
    r.add_argument("--from", dest="backup", type=Path, required=True, help="a backup folder <backup root>/<timestamp>")
    c = sub.add_parser("check-update", help="exit 10 when a rebuild is needed")
    c.add_argument("--keyhelp", type=Path, required=True)
    c.add_argument("--patches", type=Path, default=DEFAULT_PATCHES, help="patch folder to compare (default: %(default)s)")
    c.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="built assets to compare (default: %(default)s)")
    c.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT,
                   help="where a hold is recorded (default: %(default)s)")
    s = sub.add_parser("sync", help="check-update, then install when needed")
    _common(s, deploy=True)
    u = sub.add_parser("uninstall", help="move theme/lumen to the backups")
    _common(u, deploy=True)
    u.add_argument("--panel-url", help="login page of this panel; refuse while it still loads Lumen")
    u.add_argument("--insecure", action="store_true", help="do not verify the panel's TLS certificate")
    u.add_argument("--yes", action="store_true", help="the default theme is selected; go ahead without --panel-url")
    for name, text in (("hold", "stop sync from rebuilding until release or install"),
                       ("release", "let sync rebuild again after a hold or rollback")):
        h = sub.add_parser(name, help=text)
        h.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT,
                       help="where the hold is recorded (default: %(default)s)")
    sub.add_parser("version", help="print the version")
    return p


def _options(args: argparse.Namespace) -> Options:
    return Options(patches_dir=getattr(args, "patches", DEFAULT_PATCHES),
                   assets_dir=getattr(args, "assets", DEFAULT_ASSETS),
                   screenshot_fallback=getattr(args, "screenshot", DEFAULT_SCREENSHOT),
                   backup_root=getattr(args, "backup_root", DEFAULT_BACKUP_ROOT),
                   owner=getattr(args, "owner", DEFAULT_OWNER))


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
        return _run(args)
    finally:
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)


def _run(args: argparse.Namespace) -> int:
    try:
        if args.command == "version":
            print(__version__)
            return 0
        if args.command == "build":
            result = build(args.keyhelp, args.out, patches_dir=args.patches, assets_dir=args.assets,
                           screenshot_fallback=args.screenshot)
            print(f"built {result.out_dir} from default theme {result.base_version}: {len(result.patches)} patches, "
                  f"assets {result.asset_hash}, screenshot {result.screenshot}")
            report = verify(result.out_dir, args.keyhelp)
            for e in report.errors:
                print(f"error: {e}")
            print("verify: " + ("ok: " + ", ".join(report.passed) if report.ok else "FAILED"))
            return 0 if report.ok else EXIT_FAILED
        if args.command == "verify":
            report = verify(args.dir, args.keyhelp)
            for e in report.errors:
                print(f"error: {e}")
            for passed in report.passed:
                print(f"ok: {passed}")
            return 0 if report.ok else EXIT_FAILED
        if args.command == "install":
            return install(args.keyhelp, dry_run=args.dry_run, options=_options(args))
        if args.command == "rollback":
            return rollback(args.keyhelp, args.backup, options=_options(args))
        if args.command == "check-update":
            return check_update(args.keyhelp, options=_options(args))
        if args.command == "sync":
            return sync(args.keyhelp, options=_options(args))
        if args.command == "uninstall":
            return uninstall(args.keyhelp, options=_options(args), panel_url=args.panel_url,
                             insecure=args.insecure, confirmed=args.yes)
        if args.command == "hold":
            return hold(_options(args))
        if args.command == "release":
            return release(_options(args))
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
