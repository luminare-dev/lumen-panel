# 0012. Theme variants share the build, and nothing else on disk

- **Status:** accepted
- **Date:** 2026-10-21

## Context

lumen-panel builds a second theme, Lumen Dark, next to Lumen. Both are made from the same local
default theme, the same assets and almost the same template patches. An administrator may install
either or both, select one, switch between them, and roll back or remove one without touching the
other. Lumen is already installed on a live panel; its output and its backups must stay as they
are.

## Considered options

1. A second generator (or repository) for Lumen Dark.
2. One theme folder that switches between light and dark at run time (a class set by a script or
   a user setting).
3. One generator with a variant option: shared build code, patch set and assets folder, and a
   theme folder, staging and parking names, backup folder, lock, hold and Twig cache entries of
   each variant's own.

## Decision

Chosen option 3. `generator/lumen_panel/variants.py` describes each variant; every command takes
`--variant lumen|lumen-dark` (default `lumen`), and `check-update`, `sync`, `hold` and `release`
also take `all`.

- Patches: `patches/*.json` is Lumen's set. `patches/lumen-dark/*.json` replaces the files of the
  same name and adds its own; shared patches point at the theme's own files through
  `@@LUMEN_THEME_DIR@@`. The patch-set hash is taken with that token written out as the
  variant's folder, so Lumen's hash over `patches/*.json` is the one it had before the token
  existed, and an installed Lumen is not rebuilt for it.
- Assets: one `dist/assets` folder holds the stylesheets of both; a theme folder gets every file
  except the other variant's stylesheets, and its asset hash covers only its own files.
- Disk: `theme/lumen-dark`, `theme/.lumen-dark-staging-*` and `theme/.lumen-dark-previous-*`;
  backups, lock and hold in `/root/backups/lumen-panel/lumen-dark/`. Lumen keeps
  `/root/backups/lumen-panel/` itself, so existing backups and `ROLLBACK.txt` files stay valid.
  The folder name is also the theme id the panel stores when a theme is selected; it is one
  constant per variant (`folder`, by default the `--variant` value), so a different folder would
  leave the command line as it is.
- `verify` reads the variant from the build record and refuses a build in the other variant's
  folder or a template that refers to the other variant's folder; `rollback` refuses a saved theme
  of the other variant.

Option 2 was rejected: the panel's own light/dark switch is part of KeyHelp Pro
([ADR 0011](0011-lumen-dark-is-a-design-not-the-pro-dark-mode.md)), and a script-made switch would
paint the page light first and dark after.

## Consequences

- Good: one build path, tested once for both; installing, updating, holding, rolling back or
  removing one variant never changes the other; Lumen's built output stays byte for byte the same.
- Good: separate locks let the two variants be synced one after the other by the same unit
  (`sync --variant all`) without one blocking the other.
- Bad: the backup layout differs between the two (Lumen in the backup root, Lumen Dark in a
  subfolder); the documentation names both, and a prune of Lumen's run folders must match `2*`
  only, so it never removes the `lumen-dark/` folder.
- Bad: `sync --variant all` reports one exit code for two themes. A busy theme (75) wins, so the
  unit retries it; the other theme's failure shows on the last retry.
- Bad: a shared patch must fit both variants; the tests build both from the same fake panel tree,
  and the live tests check every anchor of both sets against the installed default theme.
