"""Read-only view of a KeyHelp install: where the default theme lives and what it contains.

Nothing in this module writes. The build, install and update commands use it to find the
default theme's templates and version, and to locate the Twig cache.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from . import BASE_THEME_DIR_NAME, THEME_DIR_NAME


class KeyHelpError(Exception):
    """The given folder does not look like a KeyHelp install (or the default theme is broken)."""


@dataclass(frozen=True)
class KeyHelpTree:
    root: Path

    @property
    def theme_root(self) -> Path:
        return self.root / "theme"

    @property
    def base_theme(self) -> Path:
        return self.theme_root / BASE_THEME_DIR_NAME

    @property
    def base_templates(self) -> Path:
        return self.base_theme / "templates"

    @property
    def base_settings_file(self) -> Path:
        return self.base_theme / "_settings.json"

    @property
    def lumen_theme(self) -> Path:
        return self.theme_root / THEME_DIR_NAME

    @property
    def twig_cache(self) -> Path:
        return self.root / "cache" / "twig"

    def validate(self) -> "KeyHelpTree":
        if not self.root.is_dir():
            raise KeyHelpError(f"{self.root}: not a folder")
        if not self.base_settings_file.is_file():
            raise KeyHelpError(f"{self.base_settings_file}: missing; is {self.root} the KeyHelp web root "
                               "(for example /home/keyhelp/www/keyhelp)?")
        if not (self.base_templates / "layout" / "base.twig").is_file():
            raise KeyHelpError(f"{self.base_templates}/layout/base.twig: missing; the default theme is incomplete")
        settings = self.base_settings()
        if not isinstance(settings.get("version"), str) or not settings["version"].strip():
            raise KeyHelpError(f"{self.base_settings_file}: no 'version' string")
        return self

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
