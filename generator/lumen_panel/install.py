"""Install, roll back, update and remove the Lumen theme in a KeyHelp install.

Rules this module keeps (docs/install.md explains them):
  * the default theme (theme/bulma) is only ever read;
  * an existing theme/lumen is never deleted: it is moved to <backup root>/<timestamp>/lumen;
  * the new theme is built and verified in theme/.lumen-staging-<timestamp> first, then swapped in
    with one atomic rename (renameat2 RENAME_EXCHANGE where the kernel offers it);
  * from the Twig cache only entries that record a theme/lumen/templates/ source are moved (into
    the same backup folder); everything else in the cache stays;
  * every run prints the commands that undo it.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import datetime as _dt
import json
import os
import pwd
import grp
import shutil
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import THEME_DIR_NAME, __version__
from .build import DEFAULT_ASSETS, DEFAULT_PATCHES, DEFAULT_SCREENSHOT, MANIFEST_NAME, BuildError, build
from .keyhelp import KeyHelpError, KeyHelpTree, tree_sha256
from .patches import PatchError
from .twigcache import find_theme_entries
from .verify import verify

DEFAULT_BACKUP_ROOT = Path("/root/backups/lumen-panel")
DEFAULT_OWNER = "keyhelp:keyhelp"
STAGING_PREFIX = ".lumen-staging-"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_NOT_INSTALLED = 3
EXIT_ACTIVE = 4
EXIT_UNCONFIRMED = 5
EXIT_REBUILD_NEEDED = 10

Out = Callable[[str], None]


class InstallError(Exception):
    pass


def timestamp(now: _dt.datetime | None = None) -> str:
    return (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")


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


def swap_in(staging: Path, target: Path, parking: Path) -> bool:
    """Put ``staging`` at ``target``. If ``target`` exists, its old tree ends up at ``parking``.

    Returns True if an old tree was parked. ``parking`` must be on the same file system.
    """
    if not target.exists():
        os.rename(staging, target)
        return False
    if _renameat2_exchange(staging, target):
        os.rename(staging, parking)   # staging now holds the old tree
        return True
    os.rename(target, parking)        # fallback: two renames, a gap of microseconds
    os.rename(staging, target)
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


def _backup_dir(options: Options, ts: str) -> Path:
    path = options.backup_root / ts
    if path.exists():
        raise InstallError(f"{path}: backup folder for this timestamp already exists")
    options.backup_root.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(options.backup_root, 0o700)
    except OSError:
        pass
    return path


def move_cache_entries(tree: KeyHelpTree, dest: Path) -> list[Path]:
    """Move the Lumen theme's compiled Twig templates into ``dest`` (keeps the 2-hex layout)."""
    moved: list[Path] = []
    for entry in find_theme_entries(tree.twig_cache, tree.root, THEME_DIR_NAME):
        target = dest / entry.parent.name / entry.name
        _move(entry, target)
        moved.append(target)
    return moved


def _rollback_text(tree: KeyHelpTree, backup: Path, had_previous: bool) -> str:
    me = "python3 -m lumen_panel"
    lines = ["Undo this change:"]
    if had_previous:
        lines.append(f"  {me} rollback --keyhelp {tree.root} --from {backup}")
        lines.append(f"  (manually: mv {tree.lumen_theme} {backup}/lumen.undone && cp -a {backup}/lumen "
                     f"{tree.lumen_theme} && chown -R keyhelp:keyhelp {tree.lumen_theme})")
    else:
        lines.append("  1. In KeyHelp: Configuration -> Theme -> select the default theme and save.")
        lines.append(f"  2. {me} uninstall --keyhelp {tree.root}")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------------------------
def _deploy(tree: KeyHelpTree, staging: Path, options: Options, ts: str, out: Out, *,
            owner: tuple[int, int] | None, against_keyhelp: bool = True) -> int:
    report = verify(staging, tree.root if against_keyhelp else None)
    if not report.ok:
        failed = _backup_dir(options, ts) / "failed-staging"
        _move(staging, failed)
        for e in report.errors:
            out(f"error: {e}")
        out(f"verify failed; nothing was changed. The failed build was moved to {failed}")
        return EXIT_FAILED
    out("verify: " + ", ".join(report.passed))
    set_permissions(staging, owner)
    backup = _backup_dir(options, ts)
    backup.mkdir(parents=True)
    parking = tree.theme_root / f".lumen-previous-{ts}"
    had_previous = swap_in(staging, tree.lumen_theme, parking)
    if had_previous:
        _move(parking, backup / "lumen")
        out(f"previous theme/lumen moved to {backup / 'lumen'}")
    out(f"installed {tree.lumen_theme}")
    moved = move_cache_entries(tree, backup / "twig-cache")
    out(f"twig cache: {len(moved)} compiled Lumen template(s) moved to {backup / 'twig-cache'}"
        if moved else "twig cache: no compiled Lumen templates found; nothing to move")
    text = _rollback_text(tree, backup, had_previous)
    (backup / "ROLLBACK.txt").write_text(text + "\n", encoding="utf-8")
    out(text)
    if not had_previous:
        out("Next: KeyHelp -> Configuration -> Theme -> select 'Lumen' and save.")
    return EXIT_OK


def install(keyhelp_root: Path, *, dry_run: bool = False, options: Options = Options(),
            now: _dt.datetime | None = None, out: Out = print) -> int:
    tree = KeyHelpTree(keyhelp_root).validate()
    ts = timestamp(now)
    if dry_run:
        with tempfile.TemporaryDirectory(prefix="lumen-dry-run-") as tmp:
            result = build(tree.root, Path(tmp) / "lumen", patches_dir=options.patches_dir,
                           assets_dir=options.assets_dir, screenshot_fallback=options.screenshot_fallback, now=now)
            report = verify(result.out_dir, tree.root)
            for e in report.errors:
                out(f"error: {e}")
            out("dry run: build and verify " + ("passed" if report.ok else "FAILED") +
                f" (default theme {result.base_version}, {len(result.patches)} patches, assets {result.asset_hash})")
        entries = find_theme_entries(tree.twig_cache, tree.root, THEME_DIR_NAME)
        out(f"dry run: would build in {tree.theme_root / (STAGING_PREFIX + ts)} and swap it in at {tree.lumen_theme}")
        if tree.lumen_theme.exists():
            out(f"dry run: would move the current theme/lumen to {options.backup_root / ts / 'lumen'}")
        out(f"dry run: would move {len(entries)} compiled Lumen template(s) out of {tree.twig_cache}")
        out(f"dry run: would set owner {options.owner or '(unchanged)'}, folders 755, files 644; nothing was written")
        return EXIT_OK if report.ok else EXIT_FAILED
    owner = _resolve_owner(options.owner)
    staging = tree.theme_root / (STAGING_PREFIX + ts)
    if staging.exists():
        raise InstallError(f"{staging}: already exists")
    try:
        result = build(tree.root, staging, patches_dir=options.patches_dir, assets_dir=options.assets_dir,
                       screenshot_fallback=options.screenshot_fallback, now=now)
    except (BuildError, PatchError, KeyHelpError, OSError):
        if staging.exists():
            _move(staging, _backup_dir(options, ts) / "failed-staging")
        raise
    out(f"built {staging} (default theme {result.base_version}, {len(result.patches)} patches, "
        f"assets {result.asset_hash}, screenshot {result.screenshot})")
    return _deploy(tree, staging, options, ts, out, owner=owner)


def rollback(keyhelp_root: Path, backup_dir: Path, *, options: Options = Options(),
             now: _dt.datetime | None = None, out: Out = print) -> int:
    """Put the theme saved in ``backup_dir/lumen`` back in place; the backup itself is kept."""
    tree = KeyHelpTree(keyhelp_root).validate()
    source = backup_dir / "lumen"
    if not (source / "_settings.json").is_file():
        raise InstallError(f"{source}: no saved Lumen theme here (expected {source}/_settings.json)")
    owner = _resolve_owner(options.owner)
    ts = timestamp(now)
    staging = tree.theme_root / (STAGING_PREFIX + ts)
    if staging.exists():
        raise InstallError(f"{staging}: already exists")
    shutil.copytree(source, staging, symlinks=False)
    out(f"copied {source} to {staging}")
    # Checked against its own build record: a saved theme may predate the current default theme.
    return _deploy(tree, staging, options, ts, out, owner=owner, against_keyhelp=False)


def check_update(keyhelp_root: Path, out: Out = print) -> int:
    """0: the installed theme matches the default theme and this generator; 10: rebuild; 3: not installed."""
    tree = KeyHelpTree(keyhelp_root).validate()
    settings_file = tree.lumen_theme / "_settings.json"
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
    if reasons:
        for r in reasons:
            out(f"rebuild needed: {r}")
        return EXIT_REBUILD_NEEDED
    out(f"up to date (default theme {base_version}, lumen-panel {__version__})")
    return EXIT_OK


def sync(keyhelp_root: Path, *, options: Options = Options(), now: _dt.datetime | None = None,
         out: Out = print) -> int:
    code = check_update(keyhelp_root, out)
    if code == EXIT_REBUILD_NEEDED:
        return install(keyhelp_root, options=options, now=now, out=out)
    if code == EXIT_NOT_INSTALLED:
        out("sync: Lumen is not installed; nothing to do (run 'install' first)")
        return EXIT_OK
    return code


def detect_active(panel_url: str, *, insecure: bool = False, timeout: float = 10.0) -> bool | None:
    """True if the panel's login page loads the Lumen stylesheet, False if not, None if unknown.

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
    return b"/theme/lumen/assets/lumen" in body


def uninstall(keyhelp_root: Path, *, options: Options = Options(), panel_url: str | None = None,
              insecure: bool = False, confirmed: bool = False, now: _dt.datetime | None = None,
              out: Out = print) -> int:
    tree = KeyHelpTree(keyhelp_root).validate()
    if not tree.lumen_theme.exists():
        out(f"{tree.lumen_theme}: not installed; nothing to do")
        return EXIT_OK
    out("Before removing: KeyHelp -> Configuration -> Theme -> select the default theme and save.")
    active = detect_active(panel_url, insecure=insecure) if panel_url else None
    if active is True:
        out(f"refused: {panel_url} still loads the Lumen stylesheet, so Lumen is the active theme")
        return EXIT_ACTIVE
    if active is None and not confirmed:
        why = "the panel could not be reached" if panel_url else "no --panel-url was given"
        out(f"cannot tell whether Lumen is active ({why}); after selecting the default theme, re-run with --yes")
        return EXIT_UNCONFIRMED
    ts = timestamp(now)
    backup = _backup_dir(options, ts)
    _move(tree.lumen_theme, backup / "lumen")
    moved = move_cache_entries(tree, backup / "twig-cache")
    out(f"moved {tree.lumen_theme} to {backup / 'lumen'}; {len(moved)} compiled template(s) moved")
    text = ("Undo this change:\n"
            f"  python3 -m lumen_panel rollback --keyhelp {tree.root} --from {backup}")
    (backup / "ROLLBACK.txt").write_text(text + "\n", encoding="utf-8")
    out(text)
    return EXIT_OK
