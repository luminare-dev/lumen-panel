"""The patch set: small, anchored changes to copies of the default theme's templates.

Each ``patches/*.json`` file holds one patch object or ``{"patches": [...]}``:

    {
      "id": "base-stylesheet",               unique, lower case, used in the marker comment
      "file": "layout/base.twig",            relative to the templates folder
      "description": "why the patch exists",
      "mode": "insert_before" | "insert_after" | "replace",
      "anchor": "{% block page_css %}{% endblock %}",
      "text": "<link ...>",                  may use @@LUMEN_VERSION@@ and @@LUMEN_ASSET_HASH@@
      "assets": ["lumen.css", ...]           files below assets/ the text refers to (checked by verify)
    }

The anchor must occur exactly once in the file at the time the patch is applied. If it does not
(a KeyHelp update changed the template), nothing is written and every failing patch is listed.
Every inserted text starts with the marker comment ``{# lumen-panel:<id> #}``, so ``verify`` can
prove that each patch is present exactly once.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

MODES = ("insert_before", "insert_after", "replace")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
TOKEN_RE = re.compile(r"@@([A-Z][A-Z0-9_]*)@@")
REQUIRED_KEYS = ("id", "file", "mode", "anchor", "text", "description")


class PatchError(Exception):
    """One or more patches could not be applied; ``failures`` lists each one."""

    def __init__(self, failures: list[str]):
        self.failures = failures
        super().__init__("patch set failed:\n  " + "\n  ".join(failures))


@dataclass(frozen=True)
class Patch:
    id: str
    file: str
    mode: str
    anchor: str
    text: str
    description: str
    source: str
    assets: tuple[str, ...] = field(default_factory=tuple)

    @property
    def marker(self) -> str:
        return marker(self.id)


def marker(patch_id: str) -> str:
    return "{# lumen-panel:" + patch_id + " #}"


def _safe_rel(rel: str, what: str, source: str) -> str:
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or not p.parts or "\\" in rel:
        raise PatchError([f"{source}: {what} {rel!r} must be a relative path inside the theme"])
    return p.as_posix()


def load_patches(directory: Path) -> list[Patch]:
    files = sorted(directory.glob("*.json"))
    if not files:
        raise PatchError([f"{directory}: no patch files (*.json)"])
    patches: list[Patch] = []
    problems: list[str] = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path.name}: cannot read ({exc})")
            continue
        items = data.get("patches") if isinstance(data, dict) and "patches" in data else [data]
        if not isinstance(items, list):
            problems.append(f"{path.name}: 'patches' must be a list")
            continue
        for item in items:
            if not isinstance(item, dict):
                problems.append(f"{path.name}: every patch must be a JSON object")
                continue
            missing = [k for k in REQUIRED_KEYS if not isinstance(item.get(k), str) or not item.get(k)]
            if missing:
                problems.append(f"{path.name}: missing or empty {', '.join(missing)}")
                continue
            if not ID_RE.match(item["id"]):
                problems.append(f"{path.name}: id {item['id']!r} must match {ID_RE.pattern}")
                continue
            if item["mode"] not in MODES:
                problems.append(f"{path.name} [{item['id']}]: mode {item['mode']!r} is not one of {', '.join(MODES)}")
                continue
            try:
                rel = _safe_rel(item["file"], "file", path.name)
                assets = tuple(_safe_rel(a, "asset", path.name) for a in item.get("assets", []))
            except PatchError as exc:
                problems.extend(exc.failures)
                continue
            patches.append(Patch(id=item["id"], file=rel, mode=item["mode"], anchor=item["anchor"],
                                 text=item["text"], description=item["description"], source=path.name,
                                 assets=assets))
    seen: dict[str, str] = {}
    for p in patches:
        if p.id in seen:
            problems.append(f"{p.source}: id {p.id!r} is already used in {seen[p.id]}")
        seen.setdefault(p.id, p.source)
    if problems:
        raise PatchError(problems)
    return patches


def render_text(patch: Patch, substitutions: dict[str, str]) -> str:
    unknown = sorted({m.group(1) for m in TOKEN_RE.finditer(patch.text)} - set(substitutions))
    if unknown:
        raise PatchError([f"{patch.source} [{patch.id}]: unknown token(s) {', '.join(unknown)}"])
    return patch.marker + TOKEN_RE.sub(lambda m: substitutions[m.group(1)], patch.text)


def patched_content(content: str, patch: Patch, substitutions: dict[str, str]) -> str:
    text = render_text(patch, substitutions)
    if patch.mode == "insert_before":
        return content.replace(patch.anchor, text + patch.anchor, 1)
    if patch.mode == "insert_after":
        return content.replace(patch.anchor, patch.anchor + text, 1)
    return content.replace(patch.anchor, text, 1)


def apply_patches(templates_dir: Path, patches: list[Patch], substitutions: dict[str, str]) -> list[Patch]:
    """Apply every patch in order, in memory first; write only if all of them succeed."""
    contents: dict[str, str] = {}
    failures: list[str] = []
    for patch in patches:
        path = templates_dir / patch.file
        if patch.file not in contents:
            if not path.is_file():
                failures.append(f"{patch.source} [{patch.id}]: {patch.file} does not exist in the default theme")
                continue
            contents[patch.file] = path.read_text(encoding="utf-8")
        content = contents[patch.file]
        if patch.marker in content:
            failures.append(f"{patch.source} [{patch.id}]: {patch.file} already carries this patch")
            continue
        count = content.count(patch.anchor)
        if count != 1:
            where = "not found" if count == 0 else f"found {count} times"
            failures.append(f"{patch.source} [{patch.id}]: anchor {where} in {patch.file} (expected exactly once); "
                            f"a KeyHelp update probably changed this template, see docs/upgrade.md")
            continue
        try:
            contents[patch.file] = patched_content(content, patch, substitutions)
        except PatchError as exc:
            failures.extend(exc.failures)
    if failures:
        raise PatchError(failures)
    for rel, content in contents.items():
        (templates_dir / rel).write_text(content, encoding="utf-8")
    return patches


def patched_files(patches: list[Patch]) -> list[str]:
    return sorted({p.file for p in patches})
