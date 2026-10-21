"""The patch set: small, anchored changes to copies of the default theme's templates.

Each ``patches/*.json`` file holds one patch object or ``{"patches": [...]}``:

    {
      "id": "base-stylesheet",               unique, lower case, used in the marker comment
      "file": "layout/base.twig",            relative to the templates folder
      "description": "why the patch exists",
      "mode": "insert_before" | "insert_after" | "replace",
      "anchor": "{% block page_css %}{% endblock %}",
      "text": "<link ...>",                  may use @@LUMEN_VERSION@@, @@LUMEN_ASSET_HASH@@ and
                                             @@LUMEN_THEME_DIR@@ (lumen, lumen-dark)
      "assets": ["lumen.css", ...]           files below assets/ the text refers to (checked by verify)
    }

The anchor must occur exactly once in the file at the time the patch is applied. If it does not
(a KeyHelp update changed the template), nothing is written and every failing patch is listed.
Every inserted text starts with the marker comment ``{# lumen-panel:<id> #}``, so ``verify`` can
prove that each patch is present exactly once.

``patches/*.json`` is the patch set of Lumen. A variant with an overlay folder
(``patches/lumen-dark/*.json`` for Lumen Dark) uses the same set, except that each overlay file
replaces the base file of the same name and the other overlay files are added; the files apply
in the order of their names. Paths to the theme's own files use @@LUMEN_THEME_DIR@@, so a shared
patch points at the folder of the variant it is built for.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

MODES = ("insert_before", "insert_after", "replace")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
TOKEN_RE = re.compile(r"@@([A-Z][A-Z0-9_]*)@@")
REQUIRED_KEYS = ("id", "file", "mode", "anchor", "text", "description")
# Template variables a patch text may rely on; each must still occur in the file it patches.
VAR_RE = re.compile(r"(?<![\w.])_(?:app|globals)(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


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


def patch_files(directory: Path, overlay: str | None = None) -> list[tuple[str, Path]]:
    """The patch files of one variant in the order they apply: (source name, path).

    The base set is ``directory/*.json``. With an overlay, ``directory/<overlay>/*.json`` replaces
    each base file of the same name and adds the others; the source name of an overlay file is
    ``<overlay>/<name>``."""
    files = {p.name: (p.name, p) for p in sorted(directory.glob("*.json"))}
    if overlay is not None:
        folder = directory / _safe_rel(overlay, "overlay", str(directory))
        extra = sorted(folder.glob("*.json")) if folder.is_dir() else []
        if not extra:
            raise PatchError([f"{folder}: no patch files (*.json) for this variant"])
        for p in extra:
            files[p.name] = (f"{overlay}/{p.name}", p)
    return [files[name] for name in sorted(files)]


def load_patches(directory: Path, overlay: str | None = None) -> list[Patch]:
    files = patch_files(directory, overlay)
    if not files:
        raise PatchError([f"{directory}: no patch files (*.json)"])
    patches: list[Patch] = []
    problems: list[str] = []
    for source, path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{source}: cannot read ({exc})")
            continue
        items = data.get("patches") if isinstance(data, dict) and "patches" in data else [data]
        if not isinstance(items, list):
            problems.append(f"{source}: 'patches' must be a list")
            continue
        for item in items:
            if not isinstance(item, dict):
                problems.append(f"{source}: every patch must be a JSON object")
                continue
            missing = [k for k in REQUIRED_KEYS if not isinstance(item.get(k), str) or not item.get(k)]
            if missing:
                problems.append(f"{source}: missing or empty {', '.join(missing)}")
                continue
            if not ID_RE.match(item["id"]):
                problems.append(f"{source}: id {item['id']!r} must match {ID_RE.pattern}")
                continue
            if item["mode"] not in MODES:
                problems.append(f"{source} [{item['id']}]: mode {item['mode']!r} is not one of {', '.join(MODES)}")
                continue
            try:
                rel = _safe_rel(item["file"], "file", source)
                assets = tuple(_safe_rel(a, "asset", source) for a in item.get("assets", []))
            except PatchError as exc:
                problems.extend(exc.failures)
                continue
            patches.append(Patch(id=item["id"], file=rel, mode=item["mode"], anchor=item["anchor"],
                                 text=item["text"], description=item["description"], source=source,
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


def variables_used(text: str) -> list[str]:
    """The ``_app.*`` and ``_globals.*`` names a patch text uses (sorted, without duplicates)."""
    return sorted(set(VAR_RE.findall(text)))


def patch_contents(originals: dict[str, str | None], patches: list[Patch],
                   substitutions: dict[str, str]) -> dict[str, str]:
    """Apply every patch in order, in memory. ``originals`` maps each patched file to its text
    (None: the file does not exist). Returns the patched texts or raises PatchError listing every
    patch that does not fit. Nothing is read or written here.

    Besides the anchor, every ``_app.*`` / ``_globals.*`` name a patch text uses must still occur
    in the original file: the panel renders with strict variables, so a variable a KeyHelp update
    renamed would turn into an error on every page instead of a failed build.
    """
    contents: dict[str, str] = {}
    failures: list[str] = []
    for patch in patches:
        if patch.file not in contents:
            original = originals.get(patch.file)
            if original is None:
                failures.append(f"{patch.source} [{patch.id}]: {patch.file} does not exist in the default theme")
                continue
            contents[patch.file] = original
        content = contents[patch.file]
        if patch.marker in content:
            failures.append(f"{patch.source} [{patch.id}]: {patch.file} already carries this patch")
            continue
        count = content.count(patch.anchor)
        if count != 1:
            where = "not found" if count == 0 else f"found {count} times"
            failures.append(f"{patch.source} [{patch.id}]: anchor {where} in {patch.file} (expected exactly once); "
                            f"a KeyHelp update probably changed this template, see docs/update.md")
            continue
        gone = [name for name in variables_used(patch.text) if name not in (originals.get(patch.file) or "")]
        if gone:
            failures.append(f"{patch.source} [{patch.id}]: {', '.join(gone)} no longer used in {patch.file}; "
                            "a KeyHelp update may have renamed it, see docs/update.md")
            continue
        try:
            contents[patch.file] = patched_content(content, patch, substitutions)
        except PatchError as exc:
            failures.extend(exc.failures)
    if failures:
        raise PatchError(failures)
    return contents


def read_text_exact(path: Path) -> str:
    """UTF-8 text with the line endings kept as they are (read_text would turn CRLF into LF)."""
    return path.read_bytes().decode("utf-8")


def apply_patches(templates_dir: Path, patches: list[Patch], substitutions: dict[str, str]) -> list[Patch]:
    """Apply every patch in order, in memory first; write only if all of them succeed."""
    originals: dict[str, str | None] = {}
    for rel in patched_files(patches):
        path = templates_dir / rel
        originals[rel] = read_text_exact(path) if path.is_file() else None
    contents = patch_contents(originals, patches, substitutions)
    for rel, content in contents.items():
        (templates_dir / rel).write_bytes(content.encode("utf-8"))
    return patches


def patch_set_sha256(directory: Path, overlay: str | None = None, *, theme_dir: str | None = None) -> str:
    """One sha256 over the source names and bytes of a variant's patch files, in the order they
    apply (for Lumen: every patches/*.json file, sorted).

    With ``theme_dir``, the hash covers each file with @@LUMEN_THEME_DIR@@ written out as that
    folder name, which is what the build applies: a change between the token and the literal
    folder name changes no built template and no hash (Lumen's hash is the one of the patch set
    before the token existed), while any other edit still does."""
    digest = hashlib.sha256()
    token = b"@@LUMEN_THEME_DIR@@"
    for source, path in patch_files(directory, overlay):
        data = path.read_bytes()
        if theme_dir is not None:
            data = data.replace(token, theme_dir.encode("utf-8"))
        digest.update(source.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
    return digest.hexdigest()


def patch_record(patch: Patch) -> dict:
    """Everything verify needs to apply ``patch`` again (stored in the build record)."""
    return {"id": patch.id, "file": patch.file, "source": patch.source, "mode": patch.mode,
            "anchor": patch.anchor, "text": patch.text, "description": patch.description,
            "assets": list(patch.assets)}


def patch_from_record(item: dict) -> Patch:
    if not isinstance(item, dict):
        raise PatchError(["build record: every patch must be a JSON object"])
    missing = [k for k in (*REQUIRED_KEYS, "source") if not isinstance(item.get(k), str)]
    if missing or item.get("mode") not in MODES:
        raise PatchError([f"build record: patch {item.get('id')!r} lacks {', '.join(missing) or 'a valid mode'}"])
    return Patch(id=item["id"], file=item["file"], mode=item["mode"], anchor=item["anchor"], text=item["text"],
                 description=item["description"], source=item["source"], assets=tuple(item.get("assets", [])))


def patched_files(patches: list[Patch]) -> list[str]:
    return sorted({p.file for p in patches})
