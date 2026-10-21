"""Install, roll back, update and remove a Lumen theme variant in a KeyHelp install.

Every command works on one variant (Options.variant: Lumen in theme/lumen, Lumen Dark in
theme/lumen-dark), and the variants never share a folder, a lock, a hold or a backup. Below,
<variant> is the variant's folder name and <backups> its backup folder: the backup root itself
for Lumen (/root/backups/lumen-panel, as before Lumen Dark existed), <backup root>/lumen-dark
for Lumen Dark.

Rules this module keeps (docs/install.md explains them):
  * the default theme (theme/bulma) is only ever read;
  * one run per variant at a time: install, rollback, sync, uninstall, hold and release take an
    exclusive lock on <backups>/.lock and exit 75 while another run holds it;
  * an existing theme/<variant> is never deleted: it is moved to <backups>/<timestamp>/<variant>;
  * the backup folder of a run is created before anything else is written, and folders that an
    interrupted run of the same variant left in theme/ (.<variant>-staging-*,
    .<variant>-previous-*) are moved into it;
  * the new theme is built and verified in theme/.<variant>-staging-<timestamp> first, then swapped
    in with one atomic rename (renameat2 RENAME_EXCHANGE where the kernel offers it); the replaced
    tree's _settings.json is renamed at once, so the panel never lists it as a second theme;
  * from the Twig cache only entries that record a theme/<variant>/templates/ source are moved
    (into the same backup folder); everything else in the cache stays;
  * a rollback holds the variant: sync does not rebuild it until an explicit install or `release`;
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
import shlex
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

from . import __version__
from .build import DEFAULT_ASSETS, DEFAULT_PATCHES, MANIFEST_NAME, REPO_ROOT, BuildError, asset_hash, build
from .keyhelp import KeyHelpTree, tree_sha256
from .patches import PatchError, patch_set_sha256
from .twigcache import find_theme_entries
from .variants import DEFAULT_VARIANT, LUMEN, Variant
from .verify import verify

DEFAULT_BACKUP_ROOT = Path("/root/backups/lumen-panel")
DEFAULT_OWNER = "keyhelp:keyhelp"
STAGING_PREFIX = LUMEN.staging_prefix      # ".lumen-staging-"; Lumen Dark: ".lumen-dark-staging-"
PARKING_PREFIX = LUMEN.parking_prefix      # ".lumen-previous-"; Lumen Dark: ".lumen-dark-previous-"
LEFTOVER_PREFIXES = LUMEN.leftover_prefixes
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
    screenshot_fallback: Path | None = None   # None: the variant's pre-rendered preview
    backup_root: Path = DEFAULT_BACKUP_ROOT
    owner: str = DEFAULT_OWNER          # "user:group", or "" to leave ownership as it is
    variant: Variant = DEFAULT_VARIANT

    @property
    def backups(self) -> Path:
        """The variant's own backup folder (its runs, its lock and its hold)."""
        return self.variant.backup_root(self.backup_root)


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


def _ensure_backup_root(options: Options) -> None:
    """The backup root and the variant's folder in it, readable by their owner only."""
    for folder in dict.fromkeys((options.backup_root, options.backups)):
        folder.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(folder, 0o700)


def _new_backup(options: Options, ts: str) -> Path:
    """Create this run's backup folder first, so a clash stops the run before anything is written."""
    _ensure_backup_root(options)
    path = options.backups / ts
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
    """One lumen-panel run per variant at a time (an exclusive flock on <backups>/.lock)."""
    _ensure_backup_root(options)
    fd = os.open(options.backups / LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BusyError(f"another lumen-panel run is active for {options.variant.display_name}") from exc
        yield
    finally:
        os.close(fd)   # closing the descriptor releases the lock


def leftovers(tree: KeyHelpTree, variant: Variant = DEFAULT_VARIANT) -> list[Path]:
    """Folders an interrupted run of ``variant`` left in theme/ (they may carry a _settings.json)."""
    if not tree.theme_root.is_dir():
        return []
    return sorted(p for p in tree.theme_root.iterdir() if p.name.startswith(variant.leftover_prefixes))


def installed(tree: KeyHelpTree, variant: Variant = DEFAULT_VARIANT) -> bool:
    """The variant's folder exists, or an interrupted run of it left a folder in theme/."""
    return tree.theme(variant).exists() or bool(leftovers(tree, variant))


def _clear_leftovers(tree: KeyHelpTree, backup: Path, out: Out, variant: Variant) -> None:
    for path in leftovers(tree, variant):
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


def move_cache_entries(tree: KeyHelpTree, dest: Path, variant: Variant = DEFAULT_VARIANT) -> list[Path]:
    """Move the variant's compiled Twig templates into ``dest`` (keeps the 2-hex layout).

    An entry that disappears meanwhile (the panel clears its own cache) is skipped."""
    moved: list[Path] = []
    for entry in find_theme_entries(tree.twig_cache, tree.root, variant.dir_name):
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
    path = options.backups / HOLD_NAME
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
    _ensure_backup_root(options)
    path = options.backups / HOLD_NAME
    tmp = path.with_name(HOLD_NAME + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _clear_hold(options: Options, out: Out) -> None:
    path = options.backups / HOLD_NAME
    if path.exists():
        path.unlink()
        out("hold released: sync rebuilds again when the panel changes")


def hold_text(held: dict, variant: Variant = DEFAULT_VARIANT) -> str:
    args = variant.cli_args
    if held.get("by") == "rollback":
        return f"held since {held.get('since')} after a rollback; run install{args} to resume"
    return f"held since {held.get('since')} ({held.get('by')}); run release{args} or install{args} to resume"


# --------------------------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------------------------
def undo_command() -> str:
    """How an undo line in ROLLBACK.txt starts: `python3 -m lumen_panel` only runs from the
    generator folder, and ROLLBACK.txt is usually read from somewhere else."""
    return f"cd {shlex.quote(str(REPO_ROOT / 'generator'))} && python3 -m lumen_panel"


def _select_other(v: Variant) -> str:
    return f"select the default theme (or any theme other than '{v.display_name}') and save"


def _rollback_text(tree: KeyHelpTree, backup: Path, parking: Path | None, v: Variant = DEFAULT_VARIANT) -> str:
    me = undo_command()
    target = tree.theme(v)
    saved = backup / v.dir_name
    lines = ["Undo this change:"]
    if parking is not None:
        lines.append(f"  {me} rollback{v.cli_args} --keyhelp {tree.root} --from {backup}")
        lines.append(f"  (manually: mv {target} {saved}.undone && cp -a {saved} "
                     f"{target} && chown -R keyhelp:keyhelp {target})")
        lines.append(f"  If {saved} is missing, the run stopped before the previous theme was moved: it is at")
        lines.append(f"  {parking} (with {SETTINGS} renamed to {PARKED_SETTINGS}), or, after the next run,")
        lines.append(f"  in {backup.parent}/<timestamp>/stale/{parking.name}; pass that folder to --from.")
    else:
        lines.append(f"  1. In KeyHelp: Configuration -> Appearance -> Theme -> {_select_other(v)}.")
        lines.append(f"  2. {me} uninstall{v.cli_args} --keyhelp {tree.root} --yes")
    return "\n".join(lines)


def _is_live(tree: KeyHelpTree, new_ino: int, v: Variant) -> bool:
    try:
        return os.stat(tree.theme(v)).st_ino == new_ino
    except OSError:
        return False


def _interrupted_after_swap(tree: KeyHelpTree, staging: Path, parking: Path, backup: Path, out: Out,
                            v: Variant) -> None:
    """The new build went live, then the run was stopped before the old tree was parked."""
    old = staging if os.path.lexists(staging) else parking
    with contextlib.suppress(Exception):
        _hide_settings(old)
    with contextlib.suppress(Exception):
        (backup / "ROLLBACK.txt").write_text(_rollback_text(tree, backup, old, v) + "\n", encoding="utf-8")
    out(f"interrupted after the swap: the new theme is live, the previous one is at {old}; the next run moves it "
        f"to the backups (see {backup / 'ROLLBACK.txt'})")


def _deploy(tree: KeyHelpTree, staging: Path, backup: Path, ts: str, out: Out, *,
            owner: tuple[int, int] | None, against_keyhelp: bool = True, variant: Variant = DEFAULT_VARIANT) -> int:
    v = variant
    target = tree.theme(v)
    parking = tree.theme_root / (v.parking_prefix + ts)
    new_ino: int | None = None
    try:
        report = verify(staging, tree.root if against_keyhelp else None, variant=v)
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
        had_previous = swap_in(staging, target, parking)
    except BaseException:
        if new_ino is not None and _is_live(tree, new_ino, v):
            _interrupted_after_swap(tree, staging, parking, backup, out, v)
        else:
            _park_failed(staging, backup, out)
        raise
    out(f"installed {target}")

    # From here on the new theme is live: finish every step, report what failed.
    problems: list[str] = []
    try:
        moved = move_cache_entries(tree, backup / "twig-cache", v)
        out(f"twig cache: {len(moved)} compiled {v.display_name} template(s) moved to {backup / 'twig-cache'}"
            if moved else f"twig cache: no compiled {v.display_name} templates found; nothing to move")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"moving compiled templates: {exc}")
    text = _rollback_text(tree, backup, parking if had_previous else None, v)
    try:
        (backup / "ROLLBACK.txt").write_text(text + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"writing {backup / 'ROLLBACK.txt'}: {exc}")
    if had_previous:
        try:
            _move(parking, backup / v.dir_name)
            _unhide_settings(backup / v.dir_name)
            out(f"previous theme/{v.dir_name} moved to {backup / v.dir_name}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"moving the previous theme from {parking}: {exc}")
    try:
        if LATE_CACHE_PASS_SECONDS > 0:
            time.sleep(LATE_CACHE_PASS_SECONDS)
        late = move_cache_entries(tree, backup / "twig-cache-late", v)
        if late:
            out(f"twig cache: {len(late)} more compiled {v.display_name} template(s) moved to "
                f"{backup / 'twig-cache-late'}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"second pass over the twig cache: {exc}")
    out(text)
    if problems:
        raise PostSwapError(f"the new theme is installed at {target}, but a later step failed: "
                            + "; ".join(problems) + f". See {backup / 'ROLLBACK.txt'} and docs/runbook.md")
    if not had_previous:
        out(f"Next: KeyHelp -> Configuration -> Appearance -> Theme -> select '{v.display_name}' and save.")
    return EXIT_OK


def _install(tree: KeyHelpTree, options: Options, ts: str, now: _dt.datetime | None, out: Out) -> int:
    v = options.variant
    owner = _resolve_owner(options.owner)
    backup = _new_backup(options, ts)
    _clear_leftovers(tree, backup, out, v)
    staging = tree.theme_root / (v.staging_prefix + ts)
    try:
        result = build(tree.root, staging, variant=v, patches_dir=options.patches_dir,
                       assets_dir=options.assets_dir, screenshot_fallback=options.screenshot_fallback, now=now)
    except BaseException:
        _park_failed(staging, backup, out)
        _remove_if_empty(backup)
        raise
    out(f"built {staging} ({v.display_name}, default theme {result.base_version}, {len(result.patches)} patches, "
        f"assets {result.asset_hash}, screenshot {result.screenshot})")
    try:
        code = _deploy(tree, staging, backup, ts, out, owner=owner, variant=v)
    except PostSwapError:
        _clear_hold(options, out)   # the swap itself succeeded: this install is the one that runs
        raise
    if code == EXIT_OK:
        _clear_hold(options, out)
    return code


def _dry_run(tree: KeyHelpTree, options: Options, ts: str, now: _dt.datetime | None, out: Out) -> int:
    v = options.variant
    target = tree.theme(v)
    ok = True
    with tempfile.TemporaryDirectory(prefix="lumen-dry-run-") as tmp:
        result = build(tree.root, Path(tmp) / v.dir_name, variant=v, patches_dir=options.patches_dir,
                       assets_dir=options.assets_dir, screenshot_fallback=options.screenshot_fallback, now=now)
        report = verify(result.out_dir, tree.root, variant=v)
        for e in report.errors:
            out(f"error: {e}")
        ok = report.ok
        out("dry run: build and verify " + ("passed" if report.ok else "FAILED") +
            f" ({v.display_name}, default theme {result.base_version}, {len(result.patches)} patches, "
            f"assets {result.asset_hash})")
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
    existing = options.backups
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    if existing.is_dir() and os.access(existing, os.W_OK):
        out(f"dry run: the backup folder {options.backups / ts} can be created")
    else:
        ok = False
        out(f"error: cannot create backup folders below {options.backups} ({existing} is not writable)")
    for path in leftovers(tree, v):
        out(f"dry run: would move the left-over folder {path} to {options.backups / ts / 'stale'}")
    held = read_hold(options)
    if held:
        out(f"dry run: {hold_text(held, v)} (an install releases the hold)")
    entries = find_theme_entries(tree.twig_cache, tree.root, v.dir_name)
    out(f"dry run: would build in {tree.theme_root / (v.staging_prefix + ts)} and swap it in at {target}")
    if target.exists():
        out(f"dry run: would move the current theme/{v.dir_name} to {options.backups / ts / v.dir_name}")
    out(f"dry run: would move {len(entries)} compiled {v.display_name} template(s) out of {tree.twig_cache}")
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


def _saved_name(folder: Path) -> str | None:
    for name in (SETTINGS, PARKED_SETTINGS):
        try:
            data = json.loads((folder / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        return data.get("name") if isinstance(data, dict) and isinstance(data.get("name"), str) else None
    return None


def _saved_theme(source: Path, variant: Variant = DEFAULT_VARIANT) -> Path:
    """A backup folder <ts> (with <variant>/ inside), or a saved theme folder itself, holding a
    theme of ``variant`` (a saved Lumen never goes back as Lumen Dark, or the other way round)."""
    for candidate in (source / variant.dir_name, source):
        if (candidate / SETTINGS).is_file() or (candidate / PARKED_SETTINGS).is_file():
            name = _saved_name(candidate)
            if name != variant.display_name:
                raise InstallError(f"{candidate}: a saved {name or 'unnamed'!r} theme, not {variant.display_name!r}; "
                                   "use the --variant it was built for")
            return candidate
    raise InstallError(f"{source}: no saved {variant.display_name} theme here "
                       f"(expected {source}/{variant.dir_name}/{SETTINGS})")


def rollback(keyhelp_root: Path, backup_dir: Path, *, options: Options = Options(),
             now: _dt.datetime | None = None, out: Out = print) -> int:
    """Put the theme saved in ``backup_dir`` back in place; the backup itself is kept. Then hold."""
    v = options.variant
    tree = KeyHelpTree(keyhelp_root).validate()
    source = _saved_theme(backup_dir, v)
    owner = _resolve_owner(options.owner)
    ts = timestamp(now)
    with run_lock(options):
        backup = _new_backup(options, ts)
        _clear_leftovers(tree, backup, out, v)
        staging = tree.theme_root / (v.staging_prefix + ts)
        try:
            shutil.copytree(source, staging, symlinks=False)
            _unhide_settings(staging)
        except BaseException:
            _park_failed(staging, backup, out)
            raise
        out(f"copied {source} to {staging}")
        # Checked against its own build record: a saved theme may predate the current default theme.
        code = _deploy(tree, staging, backup, ts, out, owner=owner, against_keyhelp=False, variant=v)
        if code == EXIT_OK:
            _write_hold(options, ts, "rollback", backup_dir)
            out(f"sync will not rebuild this theme until you run install{v.cli_args} (or release{v.cli_args})")
        return code


def _check_update(tree: KeyHelpTree, options: Options, out: Out) -> int:
    v = options.variant
    target = tree.theme(v)
    settings_file = target / SETTINGS
    if not settings_file.is_file():
        out(f"{target}: not installed")
        return EXIT_NOT_INSTALLED
    reasons: list[str] = []
    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    except ValueError:
        settings = {}
    try:
        manifest = json.loads((target / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    name = v.display_name
    base_version = tree.base_version()
    if settings.get("lumen_base_version") != base_version:
        reasons.append(f"default theme is {base_version}, {name} was built from {settings.get('lumen_base_version')}")
    if manifest.get("base_templates_sha256") != tree_sha256(tree.base_templates):
        reasons.append("default theme templates changed since the build")
    if manifest.get("generator_version") != __version__:
        reasons.append(f"generator is {__version__}, {name} was built by {manifest.get('generator_version')}")
    if options.assets_dir.is_dir():
        try:
            current = asset_hash(options.assets_dir, v)
        except BuildError as exc:
            current = f"unreadable ({exc})"
        if manifest.get("asset_hash") != current:
            reasons.append(f"the built assets changed since the build ({options.assets_dir}: {current}, "
                           f"{name} has {manifest.get('asset_hash')})")
    else:
        out(f"note: {options.assets_dir} not found; the built assets were not compared")
    if options.patches_dir.is_dir():
        try:
            current_patches = patch_set_sha256(options.patches_dir, v.patch_overlay, theme_dir=v.dir_name)
        except PatchError as exc:
            current_patches = f"unreadable ({'; '.join(exc.failures)})"
        if manifest.get("patches_sha256") != current_patches:
            reasons.append(f"the patch set in {options.patches_dir} changed since the build")
    else:
        out(f"note: {options.patches_dir} not found; the patch set was not compared")
    held = read_hold(options)
    if held:
        out(hold_text(held, v))
    if reasons:
        for r in reasons:
            out(f"rebuild needed: {r}")
        return EXIT_REBUILD_NEEDED
    out(f"up to date ({name}, default theme {base_version}, lumen-panel {__version__})")
    return EXIT_OK


def check_update(keyhelp_root: Path, out: Out = print, *, options: Options = Options()) -> int:
    """0: the installed theme matches the default theme, this generator, its assets and patches;
    10: rebuild needed; 3: not installed. Read-only (no lock)."""
    return _check_update(KeyHelpTree(keyhelp_root).validate(), options, out)


def sync(keyhelp_root: Path, *, options: Options = Options(), now: _dt.datetime | None = None,
         out: Out = print) -> int:
    v = options.variant
    tree = KeyHelpTree(keyhelp_root).validate()
    with run_lock(options):
        held = read_hold(options)
        if held:
            out(hold_text(held, v))
            return EXIT_OK
        code = _check_update(tree, options, out)
        if code == EXIT_REBUILD_NEEDED:
            return _install(tree, options, timestamp(now), now, out)
        if code == EXIT_NOT_INSTALLED:
            # Folders a stopped first install left (one may carry a _settings.json) go to the backups.
            if leftovers(tree, v):
                _clear_leftovers(tree, _new_backup(options, timestamp(now)), out, v)
            out(f"sync: {v.display_name} is not installed; nothing to do (run 'install{v.cli_args}' first)")
            return EXIT_OK
        if code == EXIT_OK and leftovers(tree, v):
            _clear_leftovers(tree, _new_backup(options, timestamp(now)), out, v)
        return code


def hold(options: Options = Options(), *, now: _dt.datetime | None = None, out: Out = print) -> int:
    """Stop sync from rebuilding (a maintenance window) until `release` or an explicit install."""
    args = options.variant.cli_args
    with run_lock(options):
        ts = timestamp(now)
        _write_hold(options, ts, "hold")
        out(f"held since {ts}: sync will not rebuild {options.variant.display_name} until you run "
            f"release{args} or install{args}")
        return EXIT_OK


def release(options: Options = Options(), *, out: Out = print) -> int:
    with run_lock(options):
        if read_hold(options) is None:
            out("not held; nothing to do")
            return EXIT_OK
        _clear_hold(options, out)
        return EXIT_OK


def detect_active(panel_url: str, *, insecure: bool = False, timeout: float = 10.0,
                  variant: Variant = DEFAULT_VARIANT) -> bool | None:
    """True if the panel's login page loads the variant's stylesheet, False if it loads the default
    theme's stylesheet and nothing of the variant's folder, None if unknown (unreachable, or a page
    that shows neither, such as a maintenance or error page).

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
    folder = f"/theme/{variant.dir_name}/".encode("ascii")
    if folder + b"assets/lumen" in body:
        return True
    if b"/theme/bulma/assets/css/style" in body and folder not in body:
        return False
    return None


def uninstall(keyhelp_root: Path, *, options: Options = Options(), panel_url: str | None = None,
              insecure: bool = False, confirmed: bool = False, now: _dt.datetime | None = None,
              out: Out = print) -> int:
    v = options.variant
    tree = KeyHelpTree(keyhelp_root).validate()
    target = tree.theme(v)
    if not installed(tree, v):
        out(f"{target}: not installed; nothing to do")
        return EXIT_OK
    out(f"Before removing: KeyHelp -> Configuration -> Appearance -> Theme -> {_select_other(v)}.")
    active = detect_active(panel_url, insecure=insecure, variant=v) if panel_url else None
    if active is True:
        out(f"refused: {panel_url} still loads the {v.display_name} stylesheet, so {v.display_name} is the active theme")
        return EXIT_ACTIVE
    if active is None and not confirmed:
        why = "the panel could not be reached or showed neither stylesheet" if panel_url else "no --panel-url was given"
        out(f"cannot tell whether {v.display_name} is active ({why}); after selecting another theme, re-run with --yes")
        return EXIT_UNCONFIRMED
    with run_lock(options):
        ts = timestamp(now)
        backup = _new_backup(options, ts)
        _clear_leftovers(tree, backup, out, v)
        if not target.exists():
            return EXIT_OK
        text = ("Undo this change:\n"
                f"  {undo_command()} rollback{v.cli_args} --keyhelp {tree.root} --from {backup}")
        (backup / "ROLLBACK.txt").write_text(text + "\n", encoding="utf-8")
        _move(target, backup / v.dir_name)
        moved = move_cache_entries(tree, backup / "twig-cache", v)
        out(f"moved {target} to {backup / v.dir_name}; {len(moved)} compiled template(s) moved")
        out(text)
        return EXIT_OK
