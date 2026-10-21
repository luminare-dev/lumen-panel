# Runbook

## Daily rebuild after panel updates (optional timer)

The example units [`contrib/lumen-panel-sync.service`](../contrib/lumen-panel-sync.service) and
[`contrib/lumen-panel-sync.timer`](../contrib/lumen-panel-sync.timer) run
`python3 -m lumen_panel sync` once a day in a sandbox with a 200 MB memory limit. Installing,
checking and removing them: [Keeping the theme current](update.md#daily-timer-optional). The sync
needs no Node.js: it reuses the built `dist/assets/`.

## Failure: lumen-panel-sync.service failed

| | |
|---|---|
| **Meaning** | `sync` found a rebuild was needed and the rebuild failed, almost always because a patch no longer fits a changed template (exit code 1). |
| **Impact** | None at first: the previous Lumen build stays active and nothing was changed. Its templates come from the older default theme, so new panel features may be missing on some pages until the patch set is updated. |
| **Diagnosis** | `journalctl -u lumen-panel-sync.service -n 50` lists each failing patch; `python3 -m lumen_panel check-update --keyhelp ...` shows why a rebuild is due. |
| **Mitigation** | If a page misbehaves, select the default theme under Configuration -> Theme. |
| **Fix** | Update the anchors in `patches/*.json`, run the tests, install again (see [Keeping the theme current](update.md#when-the-patch-set-does-not-fit-the-new-templates)). |

## Failure: the panel shows errors after an install

| | |
|---|---|
| **Meaning** | A template of the new build fails to render. |
| **Impact** | Pages of the panel show an error for every user of the theme. |
| **Diagnosis** | The panel's error output names the template; `python3 -m lumen_panel verify <theme/lumen> --keyhelp ...`. |
| **Mitigation** | Run the command from `ROLLBACK.txt` in the newest folder below `/root/backups/lumen-panel/` (`python3 -m lumen_panel rollback --keyhelp ... --from <backup>`), or select the default theme. |
| **Fix** | Open an issue with the template name and the KeyHelp version. |
