"""Build a Lumen theme folder from a KeyHelp install (read-only) and the project's assets.

Two variants share this build (variants.py): Lumen (theme/lumen) and Lumen Dark
(theme/lumen-dark). Output layout (``<out>/``):

    _settings.json       what KeyHelp lists under Configuration -> Appearance -> Theme
    _screenshot.png      the preview image shown there
    _lumen_build.json    build record: variant, base version and hashes, every template's sha256,
                         the patches, the asset and patch-set hashes (read by verify and
                         check-update)
    LUMEN-README.txt     where the files come from and how to rebuild
    templates/           copy of the default theme's templates (theme/default since KeyHelp 26.2,
                         theme/bulma before) with the variant's patch set applied and every
                         {{ _app.theme.url }} pointed at the default theme's folder
    assets/              the variant's stylesheets, lumen-island.js, fonts/, brand/*.svg (from
                         dist/assets; any file no variant uses stops the build, because the
                         panel's web root is public); with a customization (custom.py) its
                         overrides appended to the stylesheets and its uploads in custom/

KeyHelp's own CSS, JavaScript and images are not copied: the templates keep loading them from
the default theme's folder (/theme/default/ or /theme/bulma/), which KeyHelp updates in place.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from . import custom as _custom
from .keyhelp import KeyHelpError, KeyHelpTree, list_files, tree_sha256
from .patches import (Patch, apply_patches, load_patches, patch_record, patch_set_sha256, patched_files,
                      read_text_exact, rebase)
from .screenshot import write_screenshot
from .variants import ALL_STYLESHEETS, DEFAULT_VARIANT, Variant

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATCHES = REPO_ROOT / "patches"
DEFAULT_ASSETS = REPO_ROOT / "dist" / "assets"
# A customization (customizer ZIP, see custom.py), used when it exists; apply-custom writes it.
DEFAULT_CUSTOM = REPO_ROOT / "custom"

# Files every variant needs besides its own stylesheets; the patches add their own "assets" lists.
COMMON_ASSETS = ("lumen-island.js", "fonts/Sora[wght].ttf", "fonts/OFL.txt", "brand/favicon.svg")

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
    variant: Variant = DEFAULT_VARIANT
    custom_name: str | None = None
    base_theme: str = "default"


def load_custom(custom_dir: Path | None, assets_dir: Path) -> _custom.Custom | None:
    """The customization in ``custom_dir``, or None when there is none (no folder, or an empty one)."""
    if custom_dir is None or not custom_dir.is_dir() or not any(custom_dir.iterdir()):
        return None
    try:
        return _custom.load(custom_dir, assets_dir)
    except _custom.CustomError as exc:
        raise BuildError(f"{custom_dir}: {exc}") from exc


def cache_hash(asset_hash_value: str, custom: _custom.Custom | None) -> str:
    """The ?v= value: the asset hash, or a hash over it and the customization."""
    if custom is None:
        return asset_hash_value
    return hashlib.sha256(f"{asset_hash_value}:{custom.sha256}".encode()).hexdigest()[:12]


def asset_files(assets_dir: Path) -> list[str]:
    try:
        return list_files(assets_dir)
    except KeyHelpError as exc:  # list_files refuses symlinks
        raise BuildError(str(exc)) from exc


def required_assets(patches: list[Patch], variant: Variant = DEFAULT_VARIANT) -> list[str]:
    return sorted(set(variant.stylesheets) | set(COMMON_ASSETS) | {a for p in patches for a in p.assets})


def allowed_asset(rel: str, required: set[str]) -> bool:
    """Only files a theme uses go below theme/<variant>/assets (the panel's web root is public)."""
    if rel in required:
        return True
    folder, _, name = rel.partition("/")
    if "/" in name or not name:
        return False
    return (folder == "brand" and name.endswith(".svg")) or folder == "fonts"


def unexpected_assets(assets_dir: Path, patches: list[Patch], variant: Variant = DEFAULT_VARIANT) -> list[str]:
    """Files of the assets folder no variant uses (one folder serves every variant)."""
    known = set(required_assets(patches, variant)) | ALL_STYLESHEETS
    return [rel for rel in asset_files(assets_dir) if not allowed_asset(rel, known)]


def theme_assets(assets_dir: Path, variant: Variant = DEFAULT_VARIANT) -> list[str]:
    """The files of the assets folder that go into this variant's theme folder: everything except
    the stylesheets of the other variants (list_files order)."""
    others = ALL_STYLESHEETS - set(variant.stylesheets)
    return [rel for rel in asset_files(assets_dir) if rel not in others]


def asset_hash(assets_dir: Path, variant: Variant = DEFAULT_VARIANT) -> str:
    """The 12-character hash of a variant's assets used for cache busting (?v=) and update checks."""
    return _hash_files(assets_dir, theme_assets(assets_dir, variant))[:12]


def check_assets(assets_dir: Path, patches: list[Patch], variant: Variant = DEFAULT_VARIANT) -> list[str]:
    if not assets_dir.is_dir():
        return [f"{assets_dir}: assets folder missing; run 'npm ci && npm run build' first"]
    have = set(asset_files(assets_dir))
    return [f"{assets_dir}/{a}: missing (run 'npm run build')" for a in required_assets(patches, variant)
            if a not in have]


def settings_document(base_version: str, variant: Variant = DEFAULT_VARIANT) -> dict:
    return {
        "name": variant.display_name,
        "description": variant.description,
        "author": "Luminare Development",
        "version": __version__,
        "website": "https://luminare.tech",
        "path_to_templates": "templates/",
        "has_dark_mode": variant.has_dark_mode,
        "lumen_base_version": base_version,
    }


def _readme(result_version: str, base_version: str, variant: Variant = DEFAULT_VARIANT,
            base_theme: str = "default") -> str:
    dark = ""
    if not variant.has_dark_mode:
        dark = ("The theme is always dark. Its dark design is lumen-panel's own stylesheet on top of the\n"
                "default theme's standard (light) stylesheet. It is not the dark mode of KeyHelp Pro: it does\n"
                "not enable or unlock it, has no dark-mode switch, and loads none of its dark stylesheets or\n"
                "images.\n\n")
    return (
        variant.display_name + " theme for the KeyHelp hosting panel, built by lumen-panel " + result_version + ".\n"
        "a Luminare Development open-source project: https://github.com/luminare-dev/lumen-panel\n\n"
        + dark +
        "templates/ is a copy of the local default theme (theme/" + base_theme + ", version " + base_version + ")\n"
        "with the lumen-panel patch set applied. Those templates belong to Keyweb AG and are\n"
        "licensed with KeyHelp; do not redistribute this folder. assets/ holds lumen-panel's own\n"
        "files (MIT), the Sora font (SIL Open Font License 1.1, see assets/fonts/OFL.txt) and the\n"
        "Luminare logo files in assets/brand/ (not licensed for reuse).\n\n"
        "After a KeyHelp update, rebuild: python3 -m lumen_panel sync" + variant.cli_args
        + " --keyhelp <KeyHelp web root>\n"
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


def rebase_templates(templates_dir: Path, files: list[str], base_url: str) -> list[str]:
    """Point every {{ _app.theme.url }} of the copied templates at the default theme (patches.rebase);
    returns the files that changed. Any other use of _app.theme.url stops the build: it would
    resolve to the Lumen folder, where the default theme's files are not."""
    changed: list[str] = []
    left: list[str] = []
    for rel in files:
        if not rel.endswith(".twig"):
            continue
        path = templates_dir / rel
        text = read_text_exact(path)
        new = rebase(text, base_url)
        if "_app.theme.url" in new:
            left.append(rel)
        if new != text:
            path.write_bytes(new.encode("utf-8"))
            changed.append(rel)
    if left:
        raise BuildError("the default theme uses _app.theme.url in a way lumen-panel cannot point at "
                         f"{base_url}: {', '.join(left)}; a KeyHelp update changed the templates, see docs/update.md")
    return changed


def build(keyhelp_root: Path, out_dir: Path, *, variant: Variant = DEFAULT_VARIANT,
          patches_dir: Path = DEFAULT_PATCHES, assets_dir: Path = DEFAULT_ASSETS,
          screenshot_fallback: Path | None = None, now: _dt.datetime | None = None,
          custom_dir: Path | None = DEFAULT_CUSTOM) -> BuildResult:
    tree = KeyHelpTree(keyhelp_root).validate()
    base = tree.base_theme.resolve()
    out_resolved = out_dir.resolve()
    if out_resolved == base or base in out_resolved.parents:
        raise BuildError(f"{out_dir}: refusing to build inside the default theme ({base})")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise BuildError(f"{out_dir}: exists and is not empty")

    patches = load_patches(patches_dir, variant.patch_overlay, tree.layout)
    problems = check_assets(assets_dir, patches, variant)
    if problems:
        raise BuildError("assets incomplete:\n  " + "\n  ".join(problems))
    stray = unexpected_assets(assets_dir, patches, variant)
    if stray:
        raise BuildError(f"{assets_dir}: files the theme does not use: {', '.join(stray)}; remove them or "
                         "rebuild the assets with 'npm run build' (the panel's web root is public)")

    custom = load_custom(custom_dir, assets_dir)
    base_version = tree.base_version()
    template_files = tree.base_template_files()
    base_sha = tree_sha256(tree.base_templates)
    assets = theme_assets(assets_dir, variant)
    asset_hash_value = _hash_files(assets_dir, assets)[:12]
    cache = cache_hash(asset_hash_value, custom)
    substitutions = {"LUMEN_VERSION": __version__, "LUMEN_ASSET_HASH": cache, "LUMEN_THEME_DIR": variant.dir_name,
                     "LUMEN_BASE_URL": tree.base_url,
                     **_custom.substitutions(variant, custom, variant.dir_name, cache, tree.base_url)}

    out_dir.mkdir(parents=True, exist_ok=True)
    copied = _copy_exact(tree.base_templates, out_dir / "templates", template_files)
    # A KeyHelp update can rewrite the default theme while it is copied: the copy must be one consistent
    # state of the default theme, the same before, during and after copying.
    if _combined(template_files, copied) != base_sha or tree_sha256(tree.base_templates) != base_sha:
        raise SourceChangedError("the default theme changed during the build (a KeyHelp update is probably "
                                 "running); nothing was installed, retry later")
    apply_patches(out_dir / "templates", patches, substitutions)
    rebased = rebase_templates(out_dir / "templates", template_files, tree.base_url)
    template_sha = dict(copied)
    for rel in sorted(set(patched_files(patches)) | set(rebased)):
        template_sha[rel] = hashlib.sha256((out_dir / "templates" / rel).read_bytes()).hexdigest()
    _copy_tree(assets_dir, out_dir / "assets", assets)
    if custom is not None:
        _custom.apply_to_assets(custom, out_dir / "assets", variant.stylesheets)
    shot = write_screenshot(out_dir / "_screenshot.png", lockup_svg=assets_dir / variant.screenshot_lockup,
                            fallback=screenshot_fallback or variant.screenshot_file,
                            palette=variant.screenshot_palette)

    built_at = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "generator": "lumen-panel",
        "generator_version": __version__,
        "variant": variant.name,
        "built_at": built_at,
        "base_theme": tree.layout,
        "base_url": tree.base_url,
        "rebased_files": rebased,
        "base_version": base_version,
        "base_templates_sha256": base_sha,
        "templates": template_files,
        "template_sha256": template_sha,
        "patched_files": patched_files(patches),
        "patches": [patch_record(p) for p in patches],
        "patches_sha256": patch_set_sha256(patches_dir, variant.patch_overlay, theme_dir=variant.dir_name),
        "substitutions": substitutions,
        "assets": assets,
        "asset_hash": asset_hash_value,
        "custom": None if custom is None else {"name": custom.name, "sha256": custom.sha256,
                                               "files": [f"custom/{n}" for n in custom.media]},
    }
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out_dir / README_NAME).write_text(_readme(__version__, base_version, variant, tree.layout), encoding="utf-8")
    # _settings.json last: KeyHelp lists a folder as a theme only once this file exists.
    (out_dir / "_settings.json").write_text(json.dumps(settings_document(base_version, variant), indent=4) + "\n",
                                            encoding="utf-8")
    return BuildResult(out_dir=out_dir, base_version=base_version, base_sha256=base_sha,
                       asset_hash=asset_hash_value, base_theme=tree.layout, patches=tuple(patches), screenshot=shot, variant=variant,
                       custom_name=None if custom is None else custom.name)
