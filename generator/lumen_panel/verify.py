"""Check a built (or installed) Lumen theme folder before KeyHelp gets to see it.

Checks:
  1. _settings.json and _lumen_build.json exist and say what a Lumen build says;
  2. every default-theme template has a counterpart (against the live default theme when
     --keyhelp is given, otherwise against the build record), and there are no stale extras;
  2b. every template has the right content, byte for byte: with --keyhelp, an unpatched template
     equals the live default theme's file and a patched one equals the live file with the recorded
     patches applied again; without it, every file matches the sha256 in the build record. A
     truncated or half-copied template fails here;
  3. every patch of the build record is present exactly once (its marker comment);
  4. the patched templates pass the Twig sanity check (delimiters and block tags balanced);
  5. every theme/lumen/... file a template refers to exists below the theme folder;
  6. _screenshot.png exists.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import THEME_DISPLAY_NAME
from .build import MANIFEST_NAME
from .keyhelp import KeyHelpError, KeyHelpTree, list_files
from .patches import PatchError, marker, patch_contents, patch_from_record, read_text_exact
from .twig import asset_references, check as twig_check


@dataclass
class VerifyReport:
    errors: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_json(path: Path, report: VerifyReport) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.errors.append(f"{path.name}: missing")
        return None
    except (OSError, ValueError) as exc:
        report.errors.append(f"{path.name}: unreadable ({exc})")
        return None
    if not isinstance(data, dict):
        report.errors.append(f"{path.name}: not a JSON object")
        return None
    return data


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_contents(templates_dir: Path, files: list[str], manifest: dict, live: Path | None,
                    report: VerifyReport) -> None:
    before = len(report.errors)
    if live is None:
        recorded = manifest.get("template_sha256")
        if not isinstance(recorded, dict):
            report.errors.append("_lumen_build.json: no template_sha256 (built by an older lumen-panel); rebuild")
            return
        for rel in files:
            if recorded.get(rel) != _sha(templates_dir / rel):
                report.errors.append(f"templates/{rel}: content differs from the build record (truncated or "
                                     "changed?); rebuild")
        if len(report.errors) == before:
            report.passed.append(f"contents ({len(files)} files match the build record byte for byte)")
        return
    try:
        patches = [patch_from_record(item) for item in manifest.get("patches", [])]
    except PatchError as exc:
        report.errors.extend(exc.failures)
        return
    substitutions = manifest.get("substitutions")
    if not isinstance(substitutions, dict):
        report.errors.append("_lumen_build.json: no substitutions (built by an older lumen-panel); rebuild")
        return
    patched = {p.file for p in patches}
    for rel in files:
        if rel not in patched and _sha(templates_dir / rel) != _sha(live / rel):
            report.errors.append(f"templates/{rel}: content differs from the default theme (truncated, or the "
                                 "default theme changed since the build); rebuild")
    originals = {rel: read_text_exact(live / rel) if (live / rel).is_file() else None for rel in sorted(patched)}
    try:
        want = patch_contents(originals, patches, {str(k): str(v) for k, v in substitutions.items()})
    except PatchError as exc:
        report.errors.extend(f"live default theme: {f}" for f in exc.failures)
        return
    for rel, content in sorted(want.items()):
        path = templates_dir / rel
        if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
            report.errors.append(f"templates/{rel}: is not the live default theme's file with the recorded patches "
                                 "applied; rebuild")
    if len(report.errors) == before:
        report.passed.append(f"contents ({len(files) - len(want)} files equal the default theme, {len(want)} patched "
                             "files reproduce exactly)")


def verify(theme_dir: Path, keyhelp_root: Path | None = None) -> VerifyReport:
    report = VerifyReport()
    settings = _load_json(theme_dir / "_settings.json", report)
    manifest = _load_json(theme_dir / MANIFEST_NAME, report)
    if settings is not None:
        wrong = [k for k, v in (("name", THEME_DISPLAY_NAME), ("path_to_templates", "templates/"),
                                ("has_dark_mode", True)) if settings.get(k) != v]
        if wrong or not settings.get("lumen_base_version"):
            report.errors.append(f"_settings.json: unexpected or missing {', '.join(wrong) or 'lumen_base_version'}")
        else:
            report.passed.append("settings")
    if manifest is None:
        return report

    templates_dir = theme_dir / "templates"
    try:
        have = set(list_files(templates_dir)) if templates_dir.is_dir() else set()
    except KeyHelpError as exc:
        report.errors.append(str(exc))
        return report

    # 2. counterparts
    if keyhelp_root is not None:
        try:
            expected = set(KeyHelpTree(keyhelp_root).validate().base_template_files())
            against = "the default theme"
        except KeyHelpError as exc:
            report.errors.append(str(exc))
            return report
    else:
        expected = set(manifest.get("templates", []))
        against = "the build record"
    missing = sorted(expected - have)
    extra = sorted(have - expected)
    for rel in missing:
        report.errors.append(f"templates/{rel}: missing (present in {against}); rebuild")
    for rel in extra:
        report.errors.append(f"templates/{rel}: not in {against} (stale after a KeyHelp update?); rebuild")
    if expected and not missing and not extra:
        report.passed.append(f"templates ({len(expected)} files match {against})")

    # 2b. contents
    live = KeyHelpTree(keyhelp_root).base_templates if keyhelp_root is not None else None
    _check_contents(templates_dir, sorted(have & expected), manifest, live, report)

    # 3. patches present exactly once
    patch_ok = True
    patched: set[str] = set()
    for p in manifest.get("patches", []):
        path = templates_dir / p["file"]
        patched.add(p["file"])
        try:
            count = path.read_text(encoding="utf-8").count(marker(p["id"]))
        except OSError:
            count = 0
        if count != 1:
            patch_ok = False
            report.errors.append(f"templates/{p['file']}: patch {p['id']} present {count} times (expected 1)")
    if patch_ok and manifest.get("patches"):
        report.passed.append(f"patches ({len(manifest['patches'])} applied once each)")

    # 4. Twig sanity of the patched files
    twig_ok = True
    for rel in sorted(patched):
        path = templates_dir / rel
        if not path.is_file():
            continue
        for problem in twig_check(path.read_text(encoding="utf-8")):
            twig_ok = False
            report.errors.append(f"templates/{rel}: Twig {problem}")
    if twig_ok and patched:
        report.passed.append(f"twig syntax ({len(patched)} patched files)")

    # 5. referenced theme/lumen/ files exist
    refs_ok = True
    nrefs = 0
    for rel in sorted(have):
        if not rel.endswith(".twig"):
            continue
        for ref in asset_references((templates_dir / rel).read_text(encoding="utf-8", errors="replace")):
            nrefs += 1
            if ref.startswith("<dynamic>"):
                refs_ok = False
                report.errors.append(f"templates/{rel}: cannot resolve theme/lumen/{ref[9:]}")
            elif not (theme_dir / ref).is_file():
                refs_ok = False
                report.errors.append(f"templates/{rel}: theme/lumen/{ref} does not exist")
    if refs_ok:
        report.passed.append(f"assets ({nrefs} references resolved)")

    # 6. screenshot
    if (theme_dir / "_screenshot.png").is_file():
        report.passed.append("screenshot")
    else:
        report.errors.append("_screenshot.png: missing")
    return report
