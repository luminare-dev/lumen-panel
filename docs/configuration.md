# Configuration

The generator is configured with command-line options only; it reads no configuration file and
no environment variable (the tests read `LUMEN_KEYHELP_ROOT` to find a local install).
`python3 -m lumen_panel <command> --help` prints the same list. A test checks that every option of
the command line appears in this table.

| Option | Commands | Default | Description |
|---|---|---|---|
| `--variant` | all except `version` | `lumen` | Which theme the command works on: `lumen` (`theme/lumen`, listed as **Lumen**) or `lumen-dark` (`theme/lumen-dark`, listed as **Lumen Dark**, always dark). The two never share a folder, a staging or parking name, a backup folder, a lock, a hold or a Twig cache entry. `check-update` and `sync` also take `all`: every installed variant, one after the other. For `verify` it is optional: without it, the variant comes from the build record. |
| `--keyhelp` | all except `verify`, `version` | (required) | KeyHelp web root, for example `/home/keyhelp/www/keyhelp`. Read-only except the variant's folder (`theme/lumen` or `theme/lumen-dark`), its staging and parking folders (`theme/.lumen-staging-*`, `theme/.lumen-previous-*`, or `theme/.lumen-dark-staging-*`, `theme/.lumen-dark-previous-*`) and its entries of `cache/twig`. For `verify` it is optional: compare with the live default theme instead of the build record. |
| `--out` | `build` | (required) | Output folder; must not exist or be empty, and must not be inside the default theme. |
| `--patches` | `build`, `install`, `rollback`, `sync`, `uninstall`, `check-update` | `patches/` | Folder with the patch set: `*.json` for Lumen; Lumen Dark uses the same files, with each file of `lumen-dark/*.json` replacing the one of the same name or adding to them. `check-update` and `sync` compare the sha256 of the variant's set with the build record. |
| `--assets` | same | `dist/assets/` | Built assets (`npm run build`), one folder for both variants. Only the stylesheets of the variants (`lumen.css`, `lumen-dark.css`, `lumen-rtl.css`, `lumen-dark-rtl.css`, `lumen-night.css`, `lumen-night-rtl.css`), `lumen-island.js`, `fonts/*`, `brand/*.svg` and the files the patches list may be there; any other file stops the build. A theme folder gets every file except the other variant's stylesheets. `check-update` and `sync` compare the hash of those files with the build record. |
| `--screenshot` | same | `assets/brand/theme-screenshot.png` (Lumen), `assets/brand/theme-screenshot-dark.png` (Lumen Dark) | Preview image copied as `_screenshot.png` when PyMuPDF is not installed. |
| `--backup-root` | `install`, `rollback`, `sync`, `uninstall`, `check-update`, `hold`, `release` | `/root/backups/lumen-panel` | Where replaced themes, failed builds, left-over folders and moved cache entries go, one folder per run. Lumen uses this folder itself; Lumen Dark uses its subfolder `lumen-dark/`. Each of the two holds its own run lock (`.lock`) and hold (`HOLD`). |
| `--owner` | same | `keyhelp:keyhelp` | Owner of the installed files; `''` keeps the current owner (tests, non-root runs). |
| `--dry-run` | `install` | off | Build and verify in a temporary folder and print what would change. Writes nothing below the KeyHelp root. |
| `--from` | `rollback` | (required) | A backup folder of the same variant, `<backup root>/<timestamp>` with `lumen/` inside for Lumen or `<backup root>/lumen-dark/<timestamp>` with `lumen-dark/` inside for Lumen Dark, or a saved theme folder itself (for example `<backup root>/<timestamp>/stale/.lumen-previous-<timestamp>`). A saved theme of the other variant is refused. The backup is copied, not moved. |
| `--panel-url` | `uninstall` | none | Login page of this panel; uninstall refuses while that page still loads the variant's stylesheet. |
| `--insecure` | `uninstall` | off | Do not verify the TLS certificate of `--panel-url` (self-signed panel certificates). |
| `--yes` | `uninstall` | off | Go ahead without `--panel-url`, after another theme was selected. |

## Commands without options of their own

| Command | What it does |
|---|---|
| `hold` | Writes the variant's `HOLD` (`<backup root>/HOLD` for Lumen, `<backup root>/lumen-dark/HOLD` for Lumen Dark): `sync` then changes nothing of that variant until `release` or an explicit `install` of it. `rollback` sets the same hold, so the daily or path-triggered sync cannot put back the build that was just rolled back. `check-update` prints the hold. |
| `release` | Removes the variant's hold. |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | done, or up to date (also: `sync` while a hold is set) |
| 1 | failed: a patch did not fit, or verify found a problem (nothing was installed); or a step after the swap failed (the new theme is installed, the message says which step) |
| 2 | usage or input error (not a KeyHelp root, assets missing or unexpected files in them, output folder not empty) |
| 3 | `check-update`: the variant is not installed (with `--variant all`: none is) |
| 4 | `uninstall`: the variant is still the active theme |
| 5 | `uninstall`: not confirmed |
| 10 | `check-update`: a rebuild is needed |
| 75 | try again later: another lumen-panel run holds the lock, or the default theme changed while it was copied (a KeyHelp update was running); nothing was installed |

## Build record

Each build writes `_lumen_build.json` next to `_settings.json`: generator version, the variant
(`lumen` or `lumen-dark`; a build record without it is a Lumen build), build time, the default
theme's version and a sha256 over its templates, the list of templates with the
sha256 of each copied (or patched) file, the applied patches with their anchors and texts, the
values substituted into them, a sha256 over the patch set and the asset hash used for cache
busting (`?v=`). `verify` reads it to check every file byte for byte (against the live default
theme with `--keyhelp`, otherwise against the recorded hashes); `check-update` reads it to decide
whether a rebuild is due.
`_settings.json` carries the private key `lumen_base_version` (the default theme version the
build is based on); the panel ignores keys it does not know. Lumen declares `has_dark_mode: true`
(it follows the panel's own dark-mode switch where the panel has one), Lumen Dark
`has_dark_mode: false` (it is always dark by its own stylesheet, so the panel offers no switch
for it).

## Secrets

The project needs no secret. Secrets never go into this repository, an issue or a log. CI scans
every commit with gitleaks; a leaked secret is rotated first and removed from history second.
