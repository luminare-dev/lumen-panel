# Keeping the theme current after a KeyHelp update

A KeyHelp update replaces the default theme (`theme/bulma`) but leaves `theme/lumen` alone. Lumen's
templates are a patched copy of the default templates from the day of the last build, so after an
update they can be older than the panel. The generator notices this and rebuilds; nothing of
KeyHelp has to be downloaded, because the new default theme is already on the server.

KeyHelp is a registered trademark of Keyweb AG. lumen-panel is not affiliated with or endorsed by
Keyweb AG.

For new versions of lumen-panel itself, see [Upgrading lumen-panel](upgrade.md).

## Before a KeyHelp update: read the changelog

Read the official [KeyHelp changelog](https://changelog.keyhelp.de/) for every version between
yours and the new one before you update. Entries about the template system or engine, themes,
layouts or White Label can mean that a patch anchor no longer fits. KeyHelp carries theme folders
of their own over to a new version ("Custom themes are now transferred to the new KeyHelp version
during panel update process", KeyHelp 19.2), so `theme/lumen` stays; only its copied templates
need the rebuild below. The step-by-step order (read, update, dry run, `sync`, check) is in
[Installation, After a KeyHelp update](install.md#after-a-keyhelp-update).

## Check and rebuild by hand

```bash
cd /opt/lumen-panel/generator
sudo python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp   # 0 = current, 10 = rebuild needed
sudo python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp           # rebuild only when needed
```

`check-update` reports a rebuild when any of these differs from the build record in
`theme/lumen/_lumen_build.json`: the default theme's version, the sha256 of its templates, the
generator version, the hash of the built assets in `dist/assets/` (a new `npm run build`) or the
sha256 of the patch set in `patches/`. `sync` then runs `install`: build and verify in a staging
folder, one atomic swap, the previous build and its compiled Twig templates go to
`/root/backups/lumen-panel/<timestamp>/`. When nothing changed, `sync` only prints
`up to date (...)`; when Lumen is not installed, it does nothing and exits 0.

The build reads every default template once and checks that the default theme was the same
before, during and after copying. If a KeyHelp update rewrites it meanwhile, the build stops with
"the default theme changed during the build", installs nothing and exits 75; run it again a few
minutes later (the service below does that by itself).

The rebuild needs no Node.js: it reuses the built `dist/assets/` of the checkout.

## Rebuild automatically (optional units)

lumen-panel ships three example systemd units; it never installs them itself:

| File | What it does |
|---|---|
| [`contrib/lumen-panel-sync.service`](../contrib/lumen-panel-sync.service) | waits 120 seconds (a panel update may still be writing), then runs `python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp` once, with low priority, a 200 MB memory limit and a sandbox: only `theme/`, `cache/twig/` and `/root/backups/lumen-panel` are writable, `theme/bulma` stays read-only, there is no network. Exit code 75 (busy, or the default theme changed during the copy) starts it again 10 minutes later. |
| [`contrib/lumen-panel-sync.path`](../contrib/lumen-panel-sync.path) | starts the service when `theme/bulma/_settings.json` changes, which every panel update does (it carries the version). Lumen is rebuilt minutes after an update instead of up to a day later. |
| [`contrib/lumen-panel-sync.timer`](../contrib/lumen-panel-sync.timer) | the fallback: starts the service every day at 05:30 (plus up to 15 minutes of random delay) and catches up a missed run after a reboot. |

The units assume the checkout in `/opt/lumen-panel` and the panel in `/home/keyhelp/www/keyhelp`.
The generator runs as root from that checkout, so it must belong to root and must not be
writable by anyone else. To install them:

```bash
sudo chown -R root:root /opt/lumen-panel && sudo chmod -R go-w /opt/lumen-panel
sudo install -d -m 700 /root/backups/lumen-panel
cd /opt/lumen-panel
sudo install -m 644 contrib/lumen-panel-sync.service contrib/lumen-panel-sync.path \
  contrib/lumen-panel-sync.timer /etc/systemd/system/
# sudo systemctl edit --full lumen-panel-sync.service   # only if your paths differ (and the .path unit)
sudo systemctl daemon-reload
sudo systemctl enable --now lumen-panel-sync.path
sudo systemctl enable --now lumen-panel-sync.timer
```

Check them:

```bash
systemctl status lumen-panel-sync.path --no-pager
systemctl list-timers lumen-panel-sync.timer
sudo systemctl start lumen-panel-sync.service          # takes a little over 2 minutes (the wait)
journalctl -u lumen-panel-sync.service -n 20 --no-pager
```

A run where nothing changed logs `up to date (...)`. A failed rebuild leaves the previous build
active and marks the service as failed, so it shows in `systemctl --failed`; the
[runbook](runbook.md#failure-lumen-panel-syncservice-failed) has the steps. A missing
`dist/assets/lumen.css` also fails the unit (it is an assertion, not a condition, so it is not
skipped silently).

Inside the sandbox each writable path is its own mount, so moving the previous build from
`theme/` to `/root/backups/lumen-panel` is a copy followed by a delete, and the copies belong to
root. The backup folder is readable by root only, so this changes nothing for the panel.

To remove the units:

```bash
sudo systemctl disable --now lumen-panel-sync.path lumen-panel-sync.timer
sudo rm /etc/systemd/system/lumen-panel-sync.service /etc/systemd/system/lumen-panel-sync.path \
  /etc/systemd/system/lumen-panel-sync.timer
sudo systemctl daemon-reload
```

## Holding the theme

`rollback` puts a saved build back and sets a hold (`/root/backups/lumen-panel/HOLD`). While the
hold is set, `sync` changes nothing and prints `held since <time> after a rollback; run install
to resume`, so the units cannot put back the build you just rolled back. `check-update` still
reports whether a rebuild is due and prints the hold.

```bash
sudo python3 -m lumen_panel hold      # hold by hand, for example for a maintenance window
sudo python3 -m lumen_panel release   # let sync rebuild again
sudo python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp   # rebuild now; also releases the hold
```

## When the patch set does not fit the new templates

If `sync` stops with "the patch set does not fit this KeyHelp version", nothing was changed: the
panel keeps running on the previous Lumen build, whose templates come from the older default
theme, together with the new panel code and the updated `/theme/bulma/` stylesheets and scripts.
That can break pages until the patch set is fixed, so check the panel after every update that
`sync` could not follow, and if a page misbehaves, select **Default Theme** under
**Configuration** → **Appearance** → **Theme**. Then either update lumen-panel (a release for the
new KeyHelp version may already exist) or adjust the anchors in `patches/*.json` to the new templates (each anchor
must occur exactly once, and every `_app.*` or `_globals.*` name a patch uses must still occur in
its template), run the tests and install again; see [Troubleshooting](troubleshooting.md).
