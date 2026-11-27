"""Read-only view of a KeyHelp install: where the default theme lives and what it contains.

Nothing in this module writes. The build, install and update commands use it to find the
default theme's templates and version, and to locate the Twig cache.

Two layouts are known (the "layout" is the name of the default theme's folder):

    default  KeyHelp 26.2 and later: theme/default; templates refer to their own files with
             {{ _app.theme.url }}, which is the folder of the *active* theme
    bulma    KeyHelp before 26.2: theme/bulma; templates refer to /theme/bulma/... directly

validate() refuses an install whose folder and version do not fit one of them.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import BASE_THEME_DIR_NAME, BASE_THEME_DIR_NAMES, LEGACY_BASE_THEME_DIR_NAME, THEME_DIR_NAME

if TYPE_CHECKING:
    from .variants import Variant


class KeyHelpError(Exception):
    """The given folder does not look like a KeyHelp install (or the default theme is broken)."""


# The first KeyHelp version with theme/default (and {{ _app.theme.url }} in its templates).
DEFAULT_LAYOUT_SINCE = (26, 2)
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text: str) -> tuple[int, ...] | None:
    """(26, 2) for "26.2", (26, 1, 1) for "26.1.1"; None when it does not start with a version."""
    m = _VERSION_RE.match(text.strip())
    return tuple(int(g) for g in m.groups() if g is not None) if m else None


def layout_for_version(version: str) -> str | None:
    """The layout a KeyHelp version ships (None: not a version number)."""
    parsed = parse_version(version)
    if parsed is None:
        return None
    return BASE_THEME_DIR_NAME if parsed[:2] >= DEFAULT_LAYOUT_SINCE else LEGACY_BASE_THEME_DIR_NAME


def layout_text(layout: str) -> str:
    since = ".".join(map(str, DEFAULT_LAYOUT_SINCE))
    return (f"theme/{layout} (KeyHelp {since} and later)" if layout == BASE_THEME_DIR_NAME
            else f"theme/{layout} (KeyHelp before {since})")


@dataclass(frozen=True)
class KeyHelpTree:
    root: Path

    @property
    def theme_root(self) -> Path:
        return self.root / "theme"

    @property
    def layout(self) -> str:
        """The default theme's folder name: "default" (KeyHelp 26.2+) or "bulma" (older), the
        first one that has a _settings.json; "default" when neither has one (validate fails)."""
        for name in BASE_THEME_DIR_NAMES:
            if (self.theme_root / name / "_settings.json").is_file():
                return name
        return BASE_THEME_DIR_NAME

    @property
    def base_url(self) -> str:
        """The URL path of the default theme's folder, which the built templates load its files from."""
        return f"/theme/{self.layout}"

    @property
    def base_theme(self) -> Path:
        return self.theme_root / self.layout

    @property
    def base_templates(self) -> Path:
        return self.base_theme / "templates"

    @property
    def base_settings_file(self) -> Path:
        return self.base_theme / "_settings.json"

    @property
    def lumen_theme(self) -> Path:
        return self.theme_root / THEME_DIR_NAME

    def theme(self, variant: "Variant") -> Path:
        """The folder of one lumen-panel theme variant (theme/lumen, theme/lumen-dark)."""
        return self.theme_root / variant.dir_name

    @property
    def twig_cache(self) -> Path:
        return self.root / "cache" / "twig"

    def validate(self) -> "KeyHelpTree":
        if not self.root.is_dir():
            raise KeyHelpError(f"{self.root}: not a folder")
        if not self.base_settings_file.is_file():
            tried = " or ".join(f"theme/{n}/_settings.json" for n in BASE_THEME_DIR_NAMES)
            raise KeyHelpError(f"{self.root}: no default theme ({tried} missing); is {self.root} the KeyHelp web "
                               "root (for example /home/keyhelp/www/keyhelp)?")
        if not (self.base_templates / "layout" / "base.twig").is_file():
            raise KeyHelpError(f"{self.base_templates}/layout/base.twig: missing; the default theme is incomplete")
        settings = self.base_settings()
        if not isinstance(settings.get("version"), str) or not settings["version"].strip():
            raise KeyHelpError(f"{self.base_settings_file}: no 'version' string")
        version = settings["version"].strip()
        want = layout_for_version(version)
        if want is None:
            raise KeyHelpError(f"{self.base_settings_file}: version {version!r} is not a KeyHelp version number")
        if want != self.layout:
            raise KeyHelpError(f"KeyHelp {version} keeps its default theme in {layout_text(want)}, but this install "
                               f"has {layout_text(self.layout)}; lumen-panel does not know this layout (a KeyHelp "
                               "update may be half done). Nothing was changed.")
        return self

    def describe(self) -> str:
        """"KeyHelp 26.2, default theme in theme/default" (call after validate)."""
        return f"KeyHelp {self.base_version()}, default theme in theme/{self.layout}"

    def base_settings(self) -> dict:
        try:
            data = json.loads(self.base_settings_file.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise KeyHelpError(f"{self.base_settings_file}: cannot read ({exc})") from exc
        if not isinstance(data, dict):
            raise KeyHelpError(f"{self.base_settings_file}: not a JSON object")
        return data

    def base_version(self) -> str:
        return str(self.base_settings()["version"]).strip()

    def base_template_files(self) -> list[str]:
        """Relative POSIX paths of every regular file below the default theme's templates."""
        return list_files(self.base_templates)

    def base_templates_sha256(self) -> str:
        return tree_sha256(self.base_templates)


def list_files(folder: Path) -> list[str]:
    """Sorted relative POSIX paths of the regular files below ``folder`` (symlinks are refused)."""
    out: list[str] = []
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise KeyHelpError(f"{path}: symbolic link; refusing to follow links out of the theme")
        if path.is_file():
            out.append(path.relative_to(folder).as_posix())
    return out


def tree_sha256(folder: Path) -> str:
    """One sha256 over the relative paths and contents of every file below ``folder``."""
    digest = hashlib.sha256()
    for rel in list_files(folder):
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256((folder / rel).read_bytes()).digest())
    return digest.hexdigest()
