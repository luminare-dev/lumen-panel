"""Install, roll back, update and remove the Lumen theme in a KeyHelp install.

Rules this module keeps (docs/install.md explains them):
  * the default theme (theme/bulma) is only ever read;
  * one run at a time: install, rollback, sync, uninstall, hold and release take an exclusive
    lock on <backup root>/.lock and exit 75 while another run holds it;
  * an existing theme/lumen is never deleted: it is moved to <backup root>/<timestamp>/lumen;
  * the backup folder of a run is created before anything else is written, and folders that an
    interrupted run left in theme/ (.lumen-staging-*, .lumen-previous-*) are moved into it;
  * the new theme is built and verified in theme/.lumen-staging-<timestamp> first, then swapped in
    with one atomic rename (renameat2 RENAME_EXCHANGE where the kernel offers it); the replaced
    tree's _settings.json is renamed at once, so the panel never lists it as a second theme;
  * from the Twig cache only entries that record a theme/lumen/templates/ source are moved (into
    the same backup folder); everything else in the cache stays;
  * a rollback holds the theme: sync does not rebuild until an explicit install or `release`;
  * every run prints the commands that undo it, and writes them to ROLLBACK.txt right after the swap.
"""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.util
import datetime as _dt
import fcntl
import json
import os
import pwd
import grp
import shutil
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from . import THEME_DIR_NAME, __version__
from .build import (DEFAULT_ASSETS, DEFAULT_PATCHES, DEFAULT_SCREENSHOT, MANIFEST_NAME, BuildError, asset_hash,
                    build)
from .keyhelp import KeyHelpTree, tree_sha256
from .patches import patch_set_sha256
from .twigcache import find_theme_entries
from .verify import verify

DEFAULT_BACKUP_ROOT = Path("/root/backups/lumen-panel")
DEFAULT_OWNER = "keyhelp:keyhelp"
STAGING_PREFIX = ".lumen-staging-"
PARKING_PREFIX = ".lumen-previous-"
LEFTOVER_PREFIXES = (STAGING_PREFIX, PARKING_PREFIX)
SETTINGS = "_settings.json"
PARKED_SETTINGS = "_settings.json.parked"
LOCK_NAME = ".lock"
HOLD_NAME = "HOLD"
# A request that read an old template just before the swap can still write its compiled copy
# after the first cache pass; a second pass this many seconds later moves that one too.
LATE_CACHE_PASS_SECONDS = 2.0

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_NOT_INSTALLED = 3
EXIT_ACTIVE = 4
EXIT_UNCONFIRMED = 5
EXIT_REBUILD_NEEDED = 10
EXIT_TEMPFAIL = 75   # another run holds the lock, or the default theme changed during the build

Out = Callable[[str], None]


class InstallError(Exception):
    pass


class BusyError(InstallError):
    """Another lumen-panel run holds the lock."""


class PostSwapError(InstallError):
    """The new theme is live, but a step after the swap failed."""


def timestamp(now: _dt.datetime | None = None) -> str:
    return (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y%m%dT%H%M%S%fZ")


@dataclass(frozen=True)
class Options:
    patches_dir: Path = DEFAULT_PATCHES
    assets_dir: Path = DEFAULT_ASSETS
    screenshot_fallback: Path = DEFAULT_SCREENSHOT
    backup_root: Path = DEFAULT_BACKUP_ROOT
    owner: str = DEFAULT_OWNER          # "user:group", or "" to leave ownership as it is


# --------------------------------------------------------------------------------------------
# file system helpers
# --------------------------------------------------------------------------------------------
_RENAME_EXCHANGE = 2
_AT_FDCWD = -100


def _renameat2_exchange(a: Path, b: Path) -> bool:
    """Atomically swap two paths (Linux renameat2). False if the call is not available."""
    if not sys.platform.startswith("linux"):
        return False
    libc_name = ctypes.util.find_library("c")
    if not libc_name:
        return False
    libc = ctypes.CDLL(libc_name, use_errno=True)
    fn = getattr(libc, "renameat2", None)
    if fn is None:
        return False
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    if fn(_AT_FDCWD, os.fsencode(a), _AT_FDCWD, os.fsencode(b), _RENAME_EXCHANGE) == 0:
        return True
    err = ctypes.get_errno()
    if err in (38, 22, 95):  # ENOSYS, EINVAL (file system without support), EOPNOTSUPP
        return False
    raise OSError(err, os.strerror(err), f"{a} <-> {b}")


def _hide_settings(tree: Path) -> None:
    """Rename _settings.json, so the panel no longer lists ``tree`` as a theme."""
    with contextlib.suppress(FileNotFoundError):
        os.rename(tree / SETTINGS, tree / PARKED_SETTINGS)


def _unhide_settings(tree: Path) -> None:
    if (tree / PARKED_SETTINGS).is_file() and not (tree / SETTINGS).exists():
        os.rename(tree / PARKED_SETTINGS, tree / SETTINGS)


def swap_in(staging: Path, target: Path, parking: Path) -> bool:
    """Put ``staging`` at ``target``. If ``target`` exists, its old tree ends up at ``parking``
    with its _settings.json renamed to _settings.json.parked.

    Returns True if an old tree was parked. ``parking`` must be on the same file system.
    """
    if not target.exists():
        os.rename(staging, target)
        return False
    if _renameat2_exchange(staging, target):
        _hide_settings(staging)       # staging now holds the old tree
        os.rename(staging, parking)
        return True
    os.rename(target, parking)        # fallback: two renames, a gap of microseconds
    os.rename(staging, target)
    _hide_settings(parking)
    return True


def _resolve_owner(owner: str) -> tuple[int, int] | None:
    if not owner:
        return None
    user, _, group = owner.partition(":")
    try:
        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group or user).gr_gid
    except KeyError as exc:
        raise InstallError(f"owner {owner!r}: unknown user or group") from exc
    if os.geteuid() != 0 and uid != os.geteuid():
        raise InstallError(f"owner {owner!r}: changing ownership needs root (run as root, or pass --owner '')")
    return uid, gid


def set_permissions(tree: Path, owner: tuple[int, int] | None) -> None:
    """Folders 755, files 644, optionally owned by ``owner`` (no symlinks are created by build)."""
    for dirpath, dirnames, filenames in os.walk(tree):
        os.chmod(dirpath, 0o755)
        if owner:
            os.chown(dirpath, *owner)
        for name in filenames:
            p = os.path.join(dirpath, name)
            os.chmod(p, 0o644)
            if owner:
                os.chown(p, *owner)


def _move(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise InstallError(f"{dest}: already exists; refusing to overwrite a backup")
    shutil.move(str(src), str(dest))


def _ensure_backup_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(root, 0o700)


def _new_backup(options: Options, ts: str) -> Path:
    """Create this run's backup folder first, so a clash stops the run before anything is written."""
    _ensure_backup_root(options.backup_root)
    path = options.backup_root / ts
    try:
        path.mkdir()
    except FileExistsError as exc:
        raise InstallError(f"{path}: backup folder for this timestamp already exists") from exc
    return path


def _remove_if_empty(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.rmdir()


@contextlib.contextmanager
def run_lock(options: Options) -> Iterator[None]:
    """One lumen-panel run at a time (an exclusive flock on <backup root>/.lock)."""
    _ensure_backup_root(options.backup_root)
    fd = os.open(options.backup_root / LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BusyError("another lumen-panel run is active") from exc
        yield
    finally:
        os.close(fd)   # closing the descriptor releases the lock


def leftovers(tree: KeyHelpTree) -> list[Path]:
    """Folders an interrupted run left in theme/ (they may carry a _settings.json)."""
    if not tree.theme_root.is_dir():
        return []
    return sorted(p for p in tree.theme_root.iterdir() if p.name.startswith(LEFTOVER_PREFIXES))


def _clear_leftovers(tree: KeyHelpTree, backup: Path, out: Out) -> None:
    for path in leftovers(tree):
        dest = backup / "stale" / path.name
        _move(path, dest)
        out(f"moved a folder left by an interrupted run: {path} -> {dest}")


def _park_failed(staging: Path, backup: Path, out: Out) -> None:
    """Move a build that will not be installed out of theme/ (kept for inspection, never deleted)."""
    if not os.path.lexists(staging):
        return
    try:
        _move(staging, backup / "failed-staging")
        out(f"the unfinished build was moved to {backup / 'failed-staging'}")
    except Exception as exc:  # noqa: BLE001 (the original error is re-raised by the caller)
        out(f"warning: could not move {staging} out of theme/ ({exc}); the next run moves it")


def move_cache_entries(tree: KeyHelpTree, dest: Path) -> list[Path]:
    """Move the Lumen theme's compiled Twig templates into ``dest`` (keeps the 2-hex layout).

    An entry that disappears meanwhile (the panel clears its own cache) is skipped."""
    moved: list[Path] = []
    for entry in find_theme_entries(tree.twig_cache, tree.root, THEME_DIR_NAME):
        target = dest / entry.parent.name / entry.name
        try:
            _move(entry, target)
        except FileNotFoundError:
            continue
        moved.append(target)
    return moved


# --------------------------------------------------------------------------------------------
# hold: a rollback (or `hold`) stops sync from rebuilding until `install` or `release`
# --------------------------------------------------------------------------------------------
def read_hold(options: Options) -> dict | None:
    path = options.backup_root / HOLD_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"since": "unknown", "by": "unreadable HOLD file"}
    return data if isinstance(data, dict) else {"since": "unknown", "by": "unreadable HOLD file"}


def _write_hold(options: Options, ts: str, by: str, source: Path | None = None) -> None:
    data = {"since": ts, "by": by}
    if source is not None:
        data["from"] = str(source)
    _ensure_backup_root(options.backup_root)
    path = options.backup_root / HOLD_NAME
    tmp = path.with_name(HOLD_NAME + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _clear_hold(options: Options, out: Out) -> None:
    path = options.backup_root / HOLD_NAME
    if path.exists():
        path.unlink()
        out("hold released: sync rebuilds again when the panel changes")


def hold_text(held: dict) -> str:
    if held.get("by") == "rollback":
        return f"held since {held.get('since')} after a rollback; run install to resume"
    return f"held since {held.get('since')} ({held.get('by')}); run release or install to resume"


# --------------------------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------------------------
def _rollback_text(tree: KeyHelpTree, backup: Path, parking: Path | None) -> str:
    me = "python3 -m lumen_panel"
    lines = ["Undo this change:"]
    if parking is not None:
        lines.append(f"  {me} rollback --keyhelp {tree.root} --from {backup}")
        lines.append(f"  (manually: mv {tree.lumen_theme} {backup}/lumen.undone && cp -a {backup}/lumen "
                     f"{tree.lumen_theme} && chown -R keyhelp:keyhelp {tree.lumen_theme})")
        lines.append(f"  If {backup}/lumen is missing, the run stopped before the previous theme was moved: it is at")
        lines.append(f"  {parking} (with {SETTINGS} renamed to {PARKED_SETTINGS}), or, after the next run,")
        lines.append(f"  in <backup root>/<timestamp>/stale/{parking.name}; pass that folder to --from.")
    else:
        lines.append("  1. In KeyHelp: Configuration -> Appearance -> Theme -> select the default theme and save.")
        lines.append(f"  2. {me} uninstall --keyhelp {tree.root} --yes")
    return "\n".join(lines)


def _is_live(tree: KeyHelpTree, new_ino: int) -> bool:
    try:
        return os.stat(tree.lumen_theme).st_ino == new_ino
    except OSError:
        return False


def _interrupted_after_swap(tree: KeyHelpTree, staging: Path, parking: Path, backup: Path, out: Out) -> None:
    """The new build went live, then the run was stopped before the old tree was parked."""
    old = staging if os.path.lexists(staging) else parking
    with contextlib.suppress(Exception):
        _hide_settings(old)
    with contextlib.suppress(Exception):
        (backup / "ROLLBACK.txt").write_text(_rollback_text(tree, backup, old) + "\n", encoding="utf-8")
    out(f"interrupted after the swap: the new theme is live, the previous one is at {old}; the next run moves it "
        f"to the backups (see {backup / 'ROLLBACK.txt'})")


def _deploy(tree: KeyHelpTree, staging: Path, backup: Path, ts: str, out: Out, *,
            owner: tuple[int, int] | None, against_keyhelp: bool = True) -> int:
    parking = tree.theme_root / (PARKING_PREFIX + ts)
    new_ino: int | None = None
    try:
        report = verify(staging, tree.root if against_keyhelp else None)
        if not report.ok:
            failed = backup / "failed-staging"
            _move(staging, failed)
            for e in report.errors:
                out(f"error: {e}")
            out(f"verify failed; nothing was changed. The failed build was moved to {failed}")
            return EXIT_FAILED
        out("verify: " + ", ".join(report.passed))
        set_permissions(staging, owner)
        new_ino = os.stat(staging).st_ino
        had_previous = swap_in(staging, tree.lumen_theme, parking)
    except BaseException:
        if new_ino is not None and _is_live(tree, new_ino):
            _interrupted_after_swap(tree, staging, parking, backup, out)
        else:
            _park_failed(staging, backup, out)
        raise
    out(f"installed {tree.lumen_theme}")

    # From here on the new theme is live: finish every step, report what failed.
    problems: list[str] = []
    try:
        moved = move_cache_entries(tree, backup / "twig-cache")
        out(f"twig cache: {len(moved)} compiled Lumen template(s) moved to {backup / 'twig-cache'}"
            if moved else "twig cache: no compiled Lumen templates found; nothing to move")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"moving compiled templates: {exc}")
    text = _rollback_text(tree, backup, parking if had_previous else None)
    try:
        (backup / "ROLLBACK.txt").write_text(text + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"writing {backup / 'ROLLBACK.txt'}: {exc}")
    if had_previous:
        try:
            _move(parking, backup / "lumen")
            _unhide_settings(backup / "lumen")
            out(f"previous theme/lumen moved to {backup / 'lumen'}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"moving the previous theme from {parking}: {exc}")
    try:
        if LATE_CACHE_PASS_SECONDS > 0:
            time.sleep(LATE_CACHE_PASS_SECONDS)
        late = move_cache_entries(tree, backup / "twig-cache-late")
        if late:
            out(f"twig cache: {len(late)} more compiled Lumen template(s) moved to {backup / 'twig-cache-late'}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"second pass over the twig cache: {exc}")
    out(text)
    if problems:
        raise PostSwapError(f"the new theme is installed at {tree.lumen_theme}, but a later step failed: "
                            + "; ".join(problems) + f". See {backup / 'ROLLBACK.txt'} and docs/runbook.md")
    if not had_previous:
        out("Next: KeyHelp -> Configuration -> Appearance -> Theme -> select 'Lumen' and save.")
    return EXIT_OK


def _install(tree: KeyHelpTree, options: Options, ts: str, now: _dt.datetime | None, out: Out) -> int:
    owner = _resolve_owner(options.owner)
    backup = _new_backup(options, ts)
    _clear_leftovers(tree, backup, out)
    staging = tree.theme_root / (STAGING_PREFIX + ts)
    try:
        result = build(tree.root, staging, patches_dir=options.patches_dir, assets_dir=options.assets_dir,
                       screenshot_fallback=options.screenshot_fallback, now=now)
    except BaseException:
        _park_failed(staging, backup, out)
        _remove_if_empty(backup)
        raise
    out(f"built {staging} (default theme {result.base_version}, {len(result.patches)} patches, "
        f"assets {result.asset_hash}, screenshot {result.screenshot})")
    try:
        code = _deploy(tree, staging, backup, ts, out, owner=owner)
    except PostSwapError:
        _clear_hold(options, out)   # the swap itself succeeded: this install is the one that runs
        raise
    if code == EXIT_OK:
        _clear_hold(options, out)
    return code


def _dry_run(tree: KeyHelpTree, options: Options, ts: str, now: _dt.datetime | None, out: Out) -> int:
    ok = True
    with tempfile.TemporaryDirectory(prefix="lumen-dry-run-") as tmp:
        result = build(tree.root, Path(tmp) / "lumen", patches_dir=options.patches_dir,
                       assets_dir=options.assets_dir, screenshot_fallback=options.screenshot_fallback, now=now)
        report = verify(result.out_dir, tree.root)
        for e in report.errors:
            out(f"error: {e}")
        ok = report.ok
        out("dry run: build and verify " + ("passed" if report.ok else "FAILED") +
            f" (default theme {result.base_version}, {len(result.patches)} patches, assets {result.asset_hash})")
    try:
        owner = _resolve_owner(options.owner)
        out(f"dry run: owner {options.owner or '(unchanged)'}" + (f" is uid {owner[0]}, gid {owner[1]}" if owner else ""))
    except InstallError as exc:
        ok = False
        out(f"error: {exc}")
    if os.access(tree.theme_root, os.W_OK):
        out(f"dry run: {tree.theme_root} is writable")
    else:
        ok = False
        out(f"error: {tree.theme_root} is not writable for this user")
    existing = options.backup_root
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    if existing.is_dir() and os.access(existing, os.W_OK):
        out(f"dry run: the backup folder {options.backup_root / ts} can be created")
    else:
        ok = False
        out(f"error: cannot create backup folders below {options.backup_root} ({existing} is not writable)")
    for path in leftovers(tree):
        out(f"dry run: would move the left-over folder {path} to {options.backup_root / ts / 'stale'}")
    held = read_hold(options)
    if held:
        out(f"dry run: {hold_text(held)} (an install releases the hold)")
    entries = find_theme_entries(tree.twig_cache, tree.root, THEME_DIR_NAME)
    out(f"dry run: would build in {tree.theme_root / (STAGING_PREFIX + ts)} and swap it in at {tree.lumen_theme}")
    if tree.lumen_theme.exists():
        out(f"dry run: would move the current theme/lumen to {options.backup_root / ts / 'lumen'}")
    out(f"dry run: would move {len(entries)} compiled Lumen template(s) out of {tree.twig_cache}")
    out(f"dry run: would set owner {options.owner or '(unchanged)'}, folders 755, files 644; nothing was written")
    return EXIT_OK if ok else EXIT_FAILED


def install(keyhelp_root: Path, *, dry_run: bool = False, options: Options = Options(),
            now: _dt.datetime | None = None, out: Out = print) -> int:
    tree = KeyHelpTree(keyhelp_root).validate()
    ts = timestamp(now)
    if dry_run:
        return _dry_run(tree, options, ts, now, out)
    with run_lock(options):
        return _install(tree, options, ts, now, out)


def _saved_theme(source: Path) -> Path:
    """A backup folder <ts> (with lumen/ inside), or a saved theme folder itself."""
    for candidate in (source / "lumen", source):
        if (candidate / SETTINGS).is_file() or (candidate / PARKED_SETTINGS).is_file():
            return candidate
    raise InstallError(f"{source}: no saved Lumen theme here (expected {source}/lumen/{SETTINGS})")


def rollback(keyhelp_root: Path, backup_dir: Path, *, options: Options = Options(),
             now: _dt.datetime | None = None, out: Out = print) -> int:
    """Put the theme saved in ``backup_dir`` back in place; the backup itself is kept. Then hold."""
    tree = KeyHelpTree(keyhelp_root).validate()
    source = _saved_theme(backup_dir)
    owner = _resolve_owner(options.owner)
    ts = timestamp(now)
    with run_lock(options):
        backup = _new_backup(options, ts)
        _clear_leftovers(tree, backup, out)
        staging = tree.theme_root / (STAGING_PREFIX + ts)
        try:
            shutil.copytree(source, staging, symlinks=False)
            _unhide_settings(staging)
        except BaseException:
            _park_failed(staging, backup, out)
            raise
        out(f"copied {source} to {staging}")
        # Checked against its own build record: a saved theme may predate the current default theme.
        code = _deploy(tree, staging, backup, ts, out, owner=owner, against_keyhelp=False)
        if code == EXIT_OK:
            _write_hold(options, ts, "rollback", backup_dir)
            out("sync will not rebuild this theme until you run install (or release)")
        return code


def _check_update(tree: KeyHelpTree, options: Options, out: Out) -> int:
    settings_file = tree.lumen_theme / SETTINGS
    if not settings_file.is_file():
        out(f"{tree.lumen_theme}: not installed")
        return EXIT_NOT_INSTALLED
    reasons: list[str] = []
    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    except ValueError:
        settings = {}
    try:
        manifest = json.loads((tree.lumen_theme / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    base_version = tree.base_version()
    if settings.get("lumen_base_version") != base_version:
        reasons.append(f"default theme is {base_version}, Lumen was built from {settings.get('lumen_base_version')}")
    if manifest.get("base_templates_sha256") != tree_sha256(tree.base_templates):
        reasons.append("default theme templates changed since the build")
    if manifest.get("generator_version") != __version__:
        reasons.append(f"generator is {__version__}, Lumen was built by {manifest.get('generator_version')}")
    if options.assets_dir.is_dir():
        try:
            current = asset_hash(options.assets_dir)
        except BuildError as exc:
            current = f"unreadable ({exc})"
        if manifest.get("asset_hash") != current:
            reasons.append(f"the built assets changed since the build ({options.assets_dir}: {current}, "
                           f"Lumen has {manifest.get('asset_hash')})")
    else:
        out(f"note: {options.assets_dir} not found; the built assets were not compared")
    if options.patches_dir.is_dir():
        if manifest.get("patches_sha256") != patch_set_sha256(options.patches_dir):
            reasons.append(f"the patch set in {options.patches_dir} changed since the build")
    else:
        out(f"note: {options.patches_dir} not found; the patch set was not compared")
    held = read_hold(options)
    if held:
        out(hold_text(held))
    if reasons:
        for r in reasons:
            out(f"rebuild needed: {r}")
        return EXIT_REBUILD_NEEDED
    out(f"up to date (default theme {base_version}, lumen-panel {__version__})")
    return EXIT_OK


def check_update(keyhelp_root: Path, out: Out = print, *, options: Options = Options()) -> int:
    """0: the installed theme matches the default theme, this generator, its assets and patches;
    10: rebuild needed; 3: not installed. Read-only (no lock)."""
    return _check_update(KeyHelpTree(keyhelp_root).validate(), options, out)


def sync(keyhelp_root: Path, *, options: Options = Options(), now: _dt.datetime | None = None,
         out: Out = print) -> int:
    tree = KeyHelpTree(keyhelp_root).validate()
    with run_lock(options):
        held = read_hold(options)
        if held:
            out(hold_text(held))
            return EXIT_OK
        code = _check_update(tree, options, out)
        if code == EXIT_REBUILD_NEEDED:
            return _install(tree, options, timestamp(now), now, out)
        if code == EXIT_NOT_INSTALLED:
            out("sync: Lumen is not installed; nothing to do (run 'install' first)")
            return EXIT_OK
        if code == EXIT_OK and leftovers(tree):
            _clear_leftovers(tree, _new_backup(options, timestamp(now)), out)
        return code


def hold(options: Options = Options(), *, now: _dt.datetime | None = None, out: Out = print) -> int:
    """Stop sync from rebuilding (a maintenance window) until `release` or an explicit install."""
    with run_lock(options):
        ts = timestamp(now)
        _write_hold(options, ts, "hold")
        out(f"held since {ts}: sync will not rebuild until you run release or install")
        return EXIT_OK


def release(options: Options = Options(), *, out: Out = print) -> int:
    with run_lock(options):
        if read_hold(options) is None:
            out("not held; nothing to do")
            return EXIT_OK
        _clear_hold(options, out)
        return EXIT_OK


def detect_active(panel_url: str, *, insecure: bool = False, timeout: float = 10.0) -> bool | None:
    """True if the panel's login page loads the Lumen stylesheet, False if it loads only the
    default theme's stylesheet, None if unknown (unreachable, or a page that shows neither, such
    as a maintenance or error page).

    A plain GET of the login page, nothing else: no login, no cookies kept.
    """
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(panel_url, headers={"User-Agent": "lumen-panel/" + __version__})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:  # noqa: S310 (admin-given URL)
            body = resp.read(2_000_000)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if b"/theme/lumen/assets/lumen" in body:
        return True
    if b"/theme/bulma/assets/css/style" in body and b"/theme/lumen/" not in body:
        return False
    return None


def uninstall(keyhelp_root: Path, *, options: Options = Options(), panel_url: str | None = None,
              insecure: bool = False, confirmed: bool = False, now: _dt.datetime | None = None,
              out: Out = print) -> int:
    tree = KeyHelpTree(keyhelp_root).validate()
    if not tree.lumen_theme.exists() and not leftovers(tree):
        out(f"{tree.lumen_theme}: not installed; nothing to do")
        return EXIT_OK
    out("Before removing: KeyHelp -> Configuration -> Appearance -> Theme -> select the default theme and save.")
    active = detect_active(panel_url, insecure=insecure) if panel_url else None
    if active is True:
        out(f"refused: {panel_url} still loads the Lumen stylesheet, so Lumen is the active theme")
        return EXIT_ACTIVE
    if active is None and not confirmed:
        why = "the panel could not be reached or showed neither stylesheet" if panel_url else "no --panel-url was given"
        out(f"cannot tell whether Lumen is active ({why}); after selecting the default theme, re-run with --yes")
        return EXIT_UNCONFIRMED
    with run_lock(options):
        ts = timestamp(now)
        backup = _new_backup(options, ts)
        _clear_leftovers(tree, backup, out)
        if not tree.lumen_theme.exists():
            return EXIT_OK
        text = ("Undo this change:\n"
                f"  python3 -m lumen_panel rollback --keyhelp {tree.root} --from {backup}")
        (backup / "ROLLBACK.txt").write_text(text + "\n", encoding="utf-8")
        _move(tree.lumen_theme, backup / "lumen")
        moved = move_cache_entries(tree, backup / "twig-cache")
        out(f"moved {tree.lumen_theme} to {backup / 'lumen'}; {len(moved)} compiled template(s) moved")
        out(text)
        return EXIT_OK
