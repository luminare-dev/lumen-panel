# Runbook

Run every `python3 -m lumen_panel` command below as root from the generator folder
(`cd /opt/lumen-panel/generator`); from any other folder it fails with "No module named
lumen_panel". The commands in a `ROLLBACK.txt` change to that folder themselves.

## Automatic rebuild after panel updates (optional units)

The example units [`contrib/lumen-panel-sync.service`](../contrib/lumen-panel-sync.service),
[`contrib/lumen-panel-sync.path`](../contrib/lumen-panel-sync.path) and
[`contrib/lumen-panel-sync.timer`](../contrib/lumen-panel-sync.timer) run
`python3 -m lumen_panel sync` when the default theme changes and once a day, in a sandbox with a
200 MB memory limit. Installing, checking and removing them:
[Keeping the theme current](update.md#rebuild-automatically-optional-units). The sync needs no
Node.js: it reuses the built `dist/assets/`.

## Failure: lumen-panel-sync.service failed

| | |
|---|---|
| **Meaning** | `sync` found a rebuild was needed and the rebuild failed, almost always because a patch no longer fits a changed template (exit code 1). An assertion failure means `dist/assets/lumen.css` is missing. |
| **Impact** | The previous Lumen build stays active, and it keeps running until the patch set is fixed: its templates come from the older default theme, while the panel's code and `/theme/bulma/` assets are already the new ones. Pages that rely on a changed or new template can show errors or miss features, for every user of the theme (admins and client accounts). |
| **Diagnosis** | `journalctl -u lumen-panel-sync.service -n 50` lists each failing patch; `python3 -m lumen_panel check-update --keyhelp ...` shows why a rebuild is due. |
| **Mitigation** | Check the panel's main pages. If one misbehaves, select **Default Theme** under Configuration → Appearance → Theme until the fix is installed. |
| **Fix** | Update the anchors in `patches/*.json`, run the tests, install again (see [Keeping the theme current](update.md#when-the-patch-set-does-not-fit-the-new-templates)). |

## Failure: the panel shows errors after an install

| | |
|---|---|
| **Meaning** | A template of the new build fails to render. |
| **Impact** | Pages of the panel show an error for every user of the theme. |
| **Diagnosis** | The panel's error output names the template; `python3 -m lumen_panel verify <theme/lumen> --keyhelp ...`. |
| **Mitigation** | Run the command from `ROLLBACK.txt` in the newest folder below `/root/backups/lumen-panel/` (`python3 -m lumen_panel rollback --keyhelp ... --from <backup>`), or select the default theme. The rollback sets a hold, so the units do not rebuild the failing version again; `install` (or `release`) ends the hold once the fix is in. |
| **Fix** | Open an issue with the template name and the KeyHelp version. |

## Exit code 75: busy, or the default theme changed during the build

| | |
|---|---|
| **Meaning** | Another lumen-panel run holds the lock (`/root/backups/lumen-panel/.lock`), or a KeyHelp update rewrote the default theme while the build copied it. |
| **Impact** | None: nothing was installed. The service retries 10 minutes later. |
| **Diagnosis** | `pgrep -af lumen_panel` shows a running run; the journal names the reason. |
| **Fix** | Wait. If no run is active and it repeats, check `journalctl -u lumen-panel-sync.service`. |

## Left-over `.lumen-*` folders in theme/

| | |
|---|---|
| **Meaning** | A run was stopped (power loss, `kill -9`, out of memory) while it worked in `theme/`: `.lumen-staging-<timestamp>` is a build that was not installed, or, if the stop came right after the swap, the previous theme; `.lumen-previous-<timestamp>` is the previous theme on its way to the backups (its `_settings.json` is renamed to `_settings.json.parked`, so the panel does not list it). |
| **Impact** | Usually none. A folder that still has a `_settings.json` may be listed as a second "Lumen" under Configuration → Appearance → Theme; do not select it, because no sync updates it. The panel's web root is public, so these folders can also be downloaded until they are moved. |
| **Diagnosis** | `ls -la /home/keyhelp/www/keyhelp/theme/`; the run's `ROLLBACK.txt` in the newest backup folder names the folder it left. |
| **Fix** | Run any lumen-panel command that changes something (`install`, `sync`, `rollback`, `uninstall`): it moves every left-over folder to `/root/backups/lumen-panel/<timestamp>/stale/` and prints each one. To restore a previous theme from there: `python3 -m lumen_panel rollback --keyhelp ... --from /root/backups/lumen-panel/<timestamp>/stale/.lumen-previous-<timestamp>`. |
