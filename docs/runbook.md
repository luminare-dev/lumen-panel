# Runbook

Run the commands as root from `/opt/lumen-panel/generator`. They are written for Lumen; add
`--variant lumen-dark` for Lumen Dark (backups in `/root/backups/lumen-panel/lumen-dark/`). The
optional units are described in [docs/update.md](update.md#rebuild-automatically-optional-units).

## Failure: lumen-panel-sync.service failed

| | |
|---|---|
| **Meaning** | `sync` found a rebuild of a theme was needed and the rebuild failed, almost always because a patch no longer fits a changed template (exit code 1). The journal names the theme (`== Lumen (theme/lumen)` or `== Lumen Dark (theme/lumen-dark)`) and each failing patch. An assertion failure means `dist/assets/lumen.css` is missing. |
| **Impact** | The previous Lumen build stays active, and it keeps running until the patch set is fixed: its templates come from the older default theme, while the panel's code and `/theme/bulma/` assets are already the new ones. Pages that rely on a changed or new template can show errors or miss features, for every user of the theme (admins and client accounts). |
| **Diagnosis** | `journalctl -u lumen-panel-sync.service -n 50` lists each failing patch; `python3 -m lumen_panel check-update --variant all --keyhelp ...` shows why a rebuild is due. |
| **Mitigation** | Check the panel's main pages. If one misbehaves, select **Default Theme** under Configuration → Appearance → Theme until the fix is installed. |
| **Fix** | Update the anchors in `patches/*.json` (Lumen Dark: also `patches/lumen-dark/*.json`), run the tests, install again (see [Keeping the theme current](update.md#when-the-patch-set-does-not-fit-the-new-templates)). |

## Failure: the panel shows errors after an install

| | |
|---|---|
| **Meaning** | A template of the new build fails to render. |
| **Impact** | Pages of the panel show an error for every user of the theme. |
| **Diagnosis** | The panel's error output names the template; `python3 -m lumen_panel verify <theme/lumen> --keyhelp ...`. |
| **Mitigation** | Run the command from `ROLLBACK.txt` in the newest run folder, `ls -d /root/backups/lumen-panel/2*/ \| tail -1` (Lumen Dark: `ls -d /root/backups/lumen-panel/lumen-dark/2*/ \| tail -1`; the `lumen-dark/` folder itself is not a Lumen backup), `python3 -m lumen_panel rollback --keyhelp ... --from <backup>` (with `--variant lumen-dark` for Lumen Dark), or select the default theme or the other lumen-panel theme. The rollback sets a hold, so the units do not rebuild the failing version again; `install` (or `release`) ends the hold once the fix is in. |
| **Fix** | Open an issue with the template name and the KeyHelp version. |

## Exit code 75: busy, or the default theme changed during the build

| | |
|---|---|
| **Meaning** | Another lumen-panel run for the same theme holds its lock (`/root/backups/lumen-panel/.lock`, Lumen Dark: `/root/backups/lumen-panel/lumen-dark/.lock`), or a KeyHelp update rewrote the default theme while the build copied it. With `sync --variant all`, 75 wins over a failure of the other theme, which the journal shows as well and which comes back as exit 1 on the last retry. |
| **Impact** | None: nothing was installed. The service retries 10 minutes later. |
| **Diagnosis** | `pgrep -af lumen_panel` shows a running run; the journal names the reason. |
| **Fix** | Wait. If no run is active and it repeats, check `journalctl -u lumen-panel-sync.service`. |

## Left-over `.lumen-*` folders in theme/

| | |
|---|---|
| **Meaning** | A run was stopped (power loss, `kill -9`, out of memory) while it worked in `theme/`: `.lumen-staging-<timestamp>` (Lumen Dark: `.lumen-dark-staging-<timestamp>`) is a build that was not installed, or, if the stop came right after the swap, the previous theme; `.lumen-previous-<timestamp>` (Lumen Dark: `.lumen-dark-previous-<timestamp>`) is the previous theme on its way to the backups (its `_settings.json` is renamed to `_settings.json.parked`, so the panel does not list it). |
| **Impact** | Usually none. A folder that still has a `_settings.json` may be listed as a second "Lumen" or "Lumen Dark" under Configuration → Appearance → Theme; do not select it, because no sync updates it. The panel's web root is public, so these folders can also be downloaded until they are moved. |
| **Diagnosis** | `ls -la /home/keyhelp/www/keyhelp/theme/`; the run's `ROLLBACK.txt` in the newest run folder (`ls -d /root/backups/lumen-panel/2*/ \| tail -1`, Lumen Dark: `ls -d /root/backups/lumen-panel/lumen-dark/2*/ \| tail -1`) names the folder it left. |
| **Fix** | Run any lumen-panel command for the same theme that changes something (`install`, `sync`, also when the theme was never installed completely, `rollback`, `uninstall`): it moves that theme's left-over folders to its backups (`/root/backups/lumen-panel/<timestamp>/stale/`, Lumen Dark: `/root/backups/lumen-panel/lumen-dark/<timestamp>/stale/`) and prints each one; the other theme's folders stay for its own next run. To restore a previous theme from there: `python3 -m lumen_panel rollback --keyhelp ... --from /root/backups/lumen-panel/<timestamp>/stale/.lumen-previous-<timestamp>` (Lumen Dark: `rollback --variant lumen-dark ... --from /root/backups/lumen-panel/lumen-dark/<timestamp>/stale/.lumen-dark-previous-<timestamp>`). |
