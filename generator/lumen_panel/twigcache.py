"""Find the compiled Twig cache entries that belong to the Lumen theme, and nothing else.

KeyHelp keeps compiled templates in ``cache/twig/<2 hex>/<hex>.php``. Twig names each file after
a hash of the template's loader cache key, which is derived from the template's path. Every
compiled file ends with ``getSourceContext()``, which returns
``new Source("", "<logical name>", "<path of the .twig file>")``. That recorded path is the only
attribution used here: an entry is selected only when every Source it records lies below
``theme/lumen/templates/``. Entries of the default theme (theme/bulma/...) or of anything else
are never selected; a file that cannot be read or parsed is left alone.

Why leaving the cache alone is still safe when nothing can be attributed: the Lumen templates have
their own paths, so Twig never reuses a default-theme entry for them. On a first install no Lumen
entry exists yet. On a reinstall the copied templates get fresh modification times, so a Twig
environment with auto_reload recompiles them anyway; selected entries are moved into the backup
folder (never deleted) so that a stale compiled copy cannot survive even without auto_reload.
"""

from __future__ import annotations

import re
from pathlib import Path

_SUBDIR_RE = re.compile(r"^[0-9a-f]{2}$")
_FILE_RE = re.compile(r"^[0-9a-f]{16,128}\.php$")
_SOURCE_RE = re.compile(rb'new\s+Source\(\s*"(?:[^"\\]|\\.)*"\s*,\s*"((?:[^"\\]|\\.)*)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)')
MAX_ENTRY_BYTES = 4 * 1024 * 1024


def _unescape(raw: bytes) -> str:
    # Twig writes PHP double-quoted strings with addcslashes(..., "\0\t\"\$\\").
    return re.sub(rb"\\(.)", rb"\1", raw).decode("utf-8", errors="replace")


def recorded_sources(entry: Path) -> list[str]:
    """The template paths a compiled cache entry records (empty if it cannot be read)."""
    try:
        if entry.stat().st_size > MAX_ENTRY_BYTES:
            return []
        data = entry.read_bytes()
    except OSError:
        return []
    return [_unescape(m.group(2)) for m in _SOURCE_RE.finditer(data)]


def find_theme_entries(cache_dir: Path, keyhelp_root: Path, theme_dir_name: str) -> list[Path]:
    """Cache entries whose recorded sources all lie below theme/<theme_dir_name>/templates/."""
    if not cache_dir.is_dir():
        return []
    absolute = str((keyhelp_root / "theme" / theme_dir_name / "templates").resolve()) + "/"
    relative = f"theme/{theme_dir_name}/templates/"
    found: list[Path] = []
    for sub in sorted(cache_dir.iterdir()):
        if sub.is_symlink() or not sub.is_dir() or not _SUBDIR_RE.match(sub.name):
            continue
        for entry in sorted(sub.iterdir()):
            if entry.is_symlink() or not entry.is_file() or not _FILE_RE.match(entry.name):
                continue
            sources = recorded_sources(entry)
            if sources and all(s.startswith(absolute) or s.startswith(relative) for s in sources):
                found.append(entry)
    return found
