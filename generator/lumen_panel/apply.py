"""apply-custom: install a customizer ZIP (or a customization folder) and rebuild the themes.

Dry run by default: the ZIP is checked and every chosen variant is built and verified in a
temporary folder with it; nothing is written. With --yes:

1. every chosen variant is built and verified once more with the new customization (dry run);
2. the current customization folder (``custom/`` of the checkout) is moved to
   ``<backup root>/custom/<timestamp>/`` and the new one takes its place;
3. each variant is installed the usual way (its own backup of theme/<variant>, swap, cache);
4. if an install fails, the previous customization folder is put back and the command prints the
   rollback for the variants already rebuilt.

``--reset`` removes the customization (moved to the backups) and rebuilds with the plain Lumen look.
Undo: run apply-custom with the backup folder it printed, or --reset when there was none.
"""

from __future__ import annotations

import datetime as _dt
import shutil
from dataclasses import replace
from pathlib import Path

from . import custom as _custom
from .install import (EXIT_FAILED, EXIT_OK, EXIT_USAGE, InstallError, Options, Out, install, installed, timestamp)
from .keyhelp import KeyHelpTree
from .variants import Variant


def _describe(c: _custom.Custom, out: Out) -> None:
    out(f"customization: {c.name or '(no name)'} (sha256 {c.sha256[:12]})")
    for key, value in c.branding.items():
        if value:
            out(f"  {key}: {value}")
    for name in c.media:
        out(f"  file: custom/{name}")


def apply_custom(keyhelp_root: Path, source: Path | None, chosen: list[Variant], *, options: Options,
                 reset: bool = False, yes: bool = False, now: _dt.datetime | None = None, out: Out = print) -> int:
    tree = KeyHelpTree(keyhelp_root).validate()
    target = options.custom_dir
    if target is None:
        out("error: no customization folder (--custom)")
        return EXIT_USAGE
    names = [v for v in chosen if installed(tree, v)] if len(chosen) > 1 else chosen
    if not names:
        out("error: no Lumen theme is installed; run 'install' first, or name the variant with --variant")
        return EXIT_USAGE
    ts = timestamp(now)
    with _custom.new_temp_dir() as tmp_name:
        tmp = Path(tmp_name)
        if reset:
            new = None
            staged = tmp / "empty"
            staged.mkdir()
            out("customization: none (reset to the plain Lumen look)")
        else:
            assert source is not None
            try:
                new = _custom.read_source(source, options.assets_dir, tmp)
            except _custom.CustomError as exc:
                out(f"error: {source}: {exc}")
                return EXIT_USAGE
            _describe(new, out)
            staged = tmp / "staged"
            _custom.copy_to(new, staged)

        # 1. build and verify every variant with the new customization, writing nothing
        worst = EXIT_OK
        for v in names:
            out(f"== {v.display_name} (theme/{v.dir_name})")
            code = install(keyhelp_root, dry_run=True, options=replace(options, variant=v, custom_dir=staged), now=now,
                           out=out)
            worst = worst or code
        backup = options.backup_root / "custom" / ts
        if not yes:
            if target.exists():
                out(f"dry run: would move {target} to {backup}")
            out(f"dry run: would {'remove' if reset else 'write'} {target} and install "
                + ", ".join(v.display_name for v in names) + "; nothing was written (add --yes)")
            return worst
        if worst != EXIT_OK:
            out("error: a build with this customization failed; nothing was changed")
            return EXIT_FAILED

        # 2. swap the customization folder, keeping the old one
        had_previous = target.exists()
        if had_previous:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup))
            out(f"moved the previous customization to {backup}")
        if new is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(staged, target)
            out(f"wrote {target}")

        # 3. install each variant
        done: list[Variant] = []
        for v in names:
            out(f"== {v.display_name} (theme/{v.dir_name})")
            try:
                code = install(keyhelp_root, options=replace(options, variant=v, custom_dir=target), now=now, out=out)
            except InstallError as exc:
                out(f"error: {exc}")
                code = EXIT_FAILED
            if code != EXIT_OK:
                # 4. put the previous customization back
                if target.exists():
                    shutil.rmtree(target)
                if had_previous:
                    shutil.move(str(backup), str(target))
                out(f"error: installing {v.display_name} failed; the previous customization is back in {target}")
                for d in done:
                    out(f"  {d.display_name} was rebuilt already: undo it with 'rollback{d.cli_args} --from <the "
                        "backup folder printed above>'")
                return code
            done.append(v)
    undo = f"apply-custom {backup} --yes" if had_previous else "apply-custom --reset --yes"
    out(f"done. Undo: python3 -m lumen_panel {undo} --keyhelp {keyhelp_root}"
        + (" --variant all" if len(chosen) > 1 else chosen[0].cli_args))
    return EXIT_OK
