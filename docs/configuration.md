# Configuration

The generator is configured with command-line options only; it reads no configuration file and
no environment variable (the tests read `LUMEN_KEYHELP_ROOT` to find a local install).
`python3 -m lumen_panel <command> --help` prints the same list. A test checks that every option of
the command line appears in this table.

| Option | Commands | Default | Description |
|---|---|---|---|
| `--keyhelp` | all except `verify`, `version` | (required) | KeyHelp web root, for example `/home/keyhelp/www/keyhelp`. Read-only except `theme/lumen`, `theme/.lumen-*` and the Lumen entries of `cache/twig`. For `verify` it is optional: compare with the live default theme instead of the build record. |
| `--out` | `build` | (required) | Output folder; must not exist or be empty, and must not be inside the default theme. |
| `--patches` | `build`, `install`, `rollback`, `sync`, `uninstall`, `check-update` | `patches/` | Folder with the patch set (`*.json`). `check-update` and `sync` compare its sha256 with the build record. |
| `--assets` | same | `dist/assets/` | Built assets (`npm run build`). Only `lumen*.css`, `lumen-island.js`, `fonts/*`, `brand/*.svg` and the files the patches list may be there; any other file stops the build. `check-update` and `sync` compare their hash with the build record. |
| `--screenshot` | same | `assets/brand/theme-screenshot.png` | Preview image copied as `_screenshot.png` when PyMuPDF is not installed. |
| `--backup-root` | `install`, `rollback`, `sync`, `uninstall`, `check-update`, `hold`, `release` | `/root/backups/lumen-panel` | Where replaced themes, failed builds, left-over folders and moved cache entries go, one folder per run. It also holds the run lock (`.lock`) and the hold (`HOLD`). |
| `--owner` | same | `keyhelp:keyhelp` | Owner of the installed files; `''` keeps the current owner (tests, non-root runs). |
| `--dry-run` | `install` | off | Build and verify in a temporary folder and print what would change. Writes nothing below the KeyHelp root. |
| `--from` | `rollback` | (required) | A backup folder, `<backup root>/<timestamp>`, that contains `lumen/`, or a saved theme folder itself (for example `<backup root>/<timestamp>/stale/.lumen-previous-<timestamp>`). The backup is copied, not moved. |
| `--panel-url` | `uninstall` | none | Login page of this panel; uninstall refuses while that page still loads the Lumen stylesheet. |
| `--insecure` | `uninstall` | off | Do not verify the TLS certificate of `--panel-url` (self-signed panel certificates). |
| `--yes` | `uninstall` | off | Go ahead without `--panel-url`, after the default theme was selected. |

## Commands without options of their own

| Command | What it does |
|---|---|
| `hold` | Writes `<backup root>/HOLD`: `sync` then changes nothing until `release` or an explicit `install`. `rollback` sets the same hold, so the daily or path-triggered sync cannot put back the build that was just rolled back. `check-update` prints the hold. |
| `release` | Removes the hold. |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | done, or up to date (also: `sync` while a hold is set) |
| 1 | failed: a patch did not fit, or verify found a problem (nothing was installed); or a step after the swap failed (the new theme is installed, the message says which step) |
| 2 | usage or input error (not a KeyHelp root, assets missing or unexpected files in them, output folder not empty) |
| 3 | `check-update`: Lumen is not installed |
| 4 | `uninstall`: Lumen is still the active theme |
| 5 | `uninstall`: not confirmed |
| 10 | `check-update`: a rebuild is needed |
| 75 | try again later: another lumen-panel run holds the lock, or the default theme changed while it was copied (a KeyHelp update was running); nothing was installed |

## Build record

Each build writes `_lumen_build.json` next to `_settings.json`: generator version, build time,
the default theme's version and a sha256 over its templates, the list of templates with the
sha256 of each copied (or patched) file, the applied patches with their anchors and texts, the
values substituted into them, a sha256 over the patch set and the asset hash used for cache
busting (`?v=`). `verify` reads it to check every file byte for byte (against the live default
theme with `--keyhelp`, otherwise against the recorded hashes); `check-update` reads it to decide
whether a rebuild is due.
`_settings.json` carries the private key `lumen_base_version` (the default theme version the
build is based on); the panel ignores keys it does not know.

## Secrets

The project needs no secret. Secrets never go into this repository, an issue or a log. CI scans
every commit with gitleaks; a leaked secret is rotated first and removed from history second.
