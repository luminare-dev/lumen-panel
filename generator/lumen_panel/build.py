"""Build the Lumen theme folder from a KeyHelp install (read-only) and the project's assets.

Output layout (``<out>/``):

    _settings.json       what KeyHelp lists under Configuration -> Theme
    _screenshot.png      the preview image shown there
    _lumen_build.json    build record: base version and hashes, every template's sha256, the patches,
                         the asset and patch-set hashes (read by verify and check-update)
    LUMEN-README.txt     where the files come from and how to rebuild
    templates/           copy of theme/bulma/templates with the patch set applied
    assets/              lumen*.css, lumen-island.js, fonts/, brand/*.svg (from dist/assets; any
                         other file there stops the build, because the panel's web root is public)

KeyHelp's own CSS, JavaScript and images are not copied: the templates keep loading them from
/theme/bulma/, which KeyHelp updates in place.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import THEME_DISPLAY_NAME, __version__
from .keyhelp import KeyHelpError, KeyHelpTree, list_files, tree_sha256
from .patches import Patch, apply_patches, load_patches, patch_record, patch_set_sha256, patched_files
from .screenshot import write_screenshot

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATCHES = REPO_ROOT / "patches"
DEFAULT_ASSETS = REPO_ROOT / "dist" / "assets"
DEFAULT_SCREENSHOT = REPO_ROOT / "assets" / "brand" / "theme-screenshot.png"
SCREENSHOT_LOCKUP = "brand/luminare-lockup-compact-light.svg"

# Files the stylesheet and the patches always need; the patches add their own "assets" lists.
REQUIRED_ASSETS = (
    "lumen.css", "lumen-dark.css", "lumen-rtl.css", "lumen-dark-rtl.css",
    "lumen-island.js", "fonts/Sora[wght].ttf", "fonts/OFL.txt",
)

SETTINGS_DESCRIPTION = ("A modern theme for the KeyHelp hosting panel, a Luminare Development open-source "
                        "project (lumen-panel). Not affiliated with or endorsed by Keyweb AG. KeyHelp is a "
                        "registered trademark of Keyweb AG.")
MANIFEST_NAME = "_lumen_build.json"
README_NAME = "LUMEN-README.txt"


class BuildError(Exception):
    pass


class SourceChangedError(BuildError):
    """The default theme changed while it was being copied (a KeyHelp update is running)."""


@dataclass(frozen=True)
class BuildResult:
    out_dir: Path
    base_version: str
    base_sha256: str
    asset_hash: str
    patches: tuple[Patch, ...]
    screenshot: str


def asset_files(assets_dir: Path) -> list[str]:
    try:
        return list_files(assets_dir)
    except KeyHelpError as exc:  # list_files refuses symlinks
        raise BuildError(str(exc)) from exc


def required_assets(patches: list[Patch]) -> list[str]:
    return sorted(set(REQUIRED_ASSETS) | {a for p in patches for a in p.assets})


def allowed_asset(rel: str, required: set[str]) -> bool:
    """Only files the theme uses go below theme/lumen/assets (the panel's web root is public)."""
    if rel in required:
        return True
    folder, _, name = rel.partition("/")
    if "/" in name or not name:
        return False
    return (folder == "brand" and name.endswith(".svg")) or folder == "fonts"


def unexpected_assets(assets_dir: Path, patches: list[Patch]) -> list[str]:
    required = set(required_assets(patches))
    return [rel for rel in asset_files(assets_dir) if not allowed_asset(rel, required)]


def asset_hash(assets_dir: Path) -> str:
    """The 12-character hash of the built assets used for cache busting (?v=) and update checks."""
    return _hash_files(assets_dir, asset_files(assets_dir))[:12]


def check_assets(assets_dir: Path, patches: list[Patch]) -> list[str]:
    if not assets_dir.is_dir():
        return [f"{assets_dir}: assets folder missing; run 'npm ci && npm run build' first"]
    have = set(asset_files(assets_dir))
    return [f"{assets_dir}/{a}: missing (run 'npm run build')" for a in required_assets(patches) if a not in have]


def settings_document(base_version: str) -> dict:
    return {
        "name": THEME_DISPLAY_NAME,
        "description": SETTINGS_DESCRIPTION,
        "author": "Luminare Development",
        "version": __version__,
        "website": "https://luminare.tech",
        "path_to_templates": "templates/",
        "has_dark_mode": True,
        "lumen_base_version": base_version,
    }


def _readme(result_version: str, base_version: str) -> str:
    return (
        "Lumen theme for the KeyHelp hosting panel, built by lumen-panel " + result_version + ".\n"
        "a Luminare Development open-source project: https://github.com/luminare-dev/lumen-panel\n\n"
        "templates/ is a copy of the local default theme (theme/bulma, version " + base_version + ")\n"
        "with the lumen-panel patch set applied. Those templates belong to Keyweb AG and are\n"
        "licensed with KeyHelp; do not redistribute this folder. assets/ holds lumen-panel's own\n"
        "files (MIT), the Sora font (SIL Open Font License 1.1, see assets/fonts/OFL.txt) and the\n"
        "Luminare logo files in assets/brand/ (not licensed for reuse).\n\n"
        "After a KeyHelp update, rebuild: python3 -m lumen_panel sync --keyhelp <KeyHelp web root>\n"
        "Not affiliated with or endorsed by Keyweb AG. KeyHelp is a registered trademark of Keyweb AG.\n"
    )


def _copy_tree(src: Path, dest: Path, files: list[str]) -> None:
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        # copyfile, not copy2: the copies get fresh modification times, so Twig's auto_reload
        # never keeps a compiled template that is older than the patched source.
        shutil.copyfile(src / rel, target)


def _copy_exact(src: Path, dest: Path, files: list[str]) -> dict[str, str]:
    """Read each file once and write exactly those bytes; returns {rel: sha256 of the bytes}.

    New files, so the copies get fresh modification times (see _copy_tree)."""
    hashes: dict[str, str] = {}
    for rel in files:
        data = (src / rel).read_bytes()
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[rel] = hashlib.sha256(data).hexdigest()
    return hashes


def _combined(files: list[str], hashes: dict[str, str]) -> str:
    """The same value tree_sha256 gives for a folder whose files have these hashes. ``files`` must
    be in list_files order (sorted Path objects, which differs from sorting the strings)."""
    digest = hashlib.sha256()
    for rel in files:
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(bytes.fromhex(hashes[rel]))
    return digest.hexdigest()


def _hash_files(folder: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in files:
        digest.update(rel.encode("utf-8") + b"\0" + hashlib.sha256((folder / rel).read_bytes()).digest())
    return digest.hexdigest()


def build(keyhelp_root: Path, out_dir: Path, *, patches_dir: Path = DEFAULT_PATCHES,
          assets_dir: Path = DEFAULT_ASSETS, screenshot_fallback: Path = DEFAULT_SCREENSHOT,
          now: _dt.datetime | None = None) -> BuildResult:
    tree = KeyHelpTree(keyhelp_root).validate()
    base = tree.base_theme.resolve()
    out_resolved = out_dir.resolve()
    if out_resolved == base or base in out_resolved.parents:
        raise BuildError(f"{out_dir}: refusing to build inside the default theme ({base})")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise BuildError(f"{out_dir}: exists and is not empty")

    patches = load_patches(patches_dir)
    problems = check_assets(assets_dir, patches)
    if problems:
        raise BuildError("assets incomplete:\n  " + "\n  ".join(problems))
    stray = unexpected_assets(assets_dir, patches)
    if stray:
        raise BuildError(f"{assets_dir}: files the theme does not use: {', '.join(stray)}; remove them or "
                         "rebuild the assets with 'npm run build' (the panel's web root is public)")

    base_version = tree.base_version()
    template_files = tree.base_template_files()
    base_sha = tree_sha256(tree.base_templates)
    assets = asset_files(assets_dir)
    asset_hash_value = _hash_files(assets_dir, assets)[:12]
    substitutions = {"LUMEN_VERSION": __version__, "LUMEN_ASSET_HASH": asset_hash_value}

    out_dir.mkdir(parents=True, exist_ok=True)
    copied = _copy_exact(tree.base_templates, out_dir / "templates", template_files)
    # A KeyHelp update can rewrite theme/bulma while it is copied: the copy must be one consistent
    # state of the default theme, the same before, during and after copying.
    if _combined(template_files, copied) != base_sha or tree_sha256(tree.base_templates) != base_sha:
        raise SourceChangedError("the default theme changed during the build (a KeyHelp update is probably "
                                 "running); nothing was installed, retry later")
    apply_patches(out_dir / "templates", patches, substitutions)
    template_sha = dict(copied)
    for rel in patched_files(patches):
        template_sha[rel] = hashlib.sha256((out_dir / "templates" / rel).read_bytes()).hexdigest()
    _copy_tree(assets_dir, out_dir / "assets", assets)
    shot = write_screenshot(out_dir / "_screenshot.png", lockup_svg=assets_dir / SCREENSHOT_LOCKUP,
                            fallback=screenshot_fallback)

    built_at = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "generator": "lumen-panel",
        "generator_version": __version__,
        "built_at": built_at,
        "base_theme": "bulma",
        "base_version": base_version,
        "base_templates_sha256": base_sha,
        "templates": template_files,
        "template_sha256": template_sha,
        "patched_files": patched_files(patches),
        "patches": [patch_record(p) for p in patches],
        "patches_sha256": patch_set_sha256(patches_dir),
        "substitutions": substitutions,
        "assets": assets,
        "asset_hash": asset_hash_value,
    }
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out_dir / README_NAME).write_text(_readme(__version__, base_version), encoding="utf-8")
    # _settings.json last: KeyHelp lists a folder as a theme only once this file exists.
    (out_dir / "_settings.json").write_text(json.dumps(settings_document(base_version), indent=4) + "\n",
                                            encoding="utf-8")
    return BuildResult(out_dir=out_dir, base_version=base_version, base_sha256=base_sha,
                       asset_hash=asset_hash_value, patches=tuple(patches), screenshot=shot)
