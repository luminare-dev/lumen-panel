# Keeping the theme current after a KeyHelp update

A KeyHelp update replaces the default theme (`theme/bulma`) but leaves `theme/lumen` alone. Lumen's
templates are a patched copy of the default templates from the day of the last build, so after an
update they can be older than the panel. The generator notices this and rebuilds; nothing of
KeyHelp has to be downloaded, because the new default theme is already on the server.

For new versions of lumen-panel itself, see [Upgrading lumen-panel](upgrade.md).

## Check and rebuild by hand

```bash
cd generator
sudo python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp   # 0 = current, 10 = rebuild needed
sudo python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp           # rebuild only when needed
```

`check-update` reports a rebuild when the default theme's version, the sha256 of its templates or
the generator version differ from the build record in `theme/lumen/_lumen_build.json`. `sync` then
runs `install`: build and verify in a staging folder, one atomic swap, the previous build and its
compiled Twig templates go to `/root/backups/lumen-panel/<timestamp>/`. When nothing changed,
`sync` only prints `up to date (...)`; when Lumen is not installed, it does nothing and exits 0.

The rebuild needs no Node.js: it reuses the built `dist/assets/` of the checkout.

## Daily timer (optional)

lumen-panel ships two example systemd units; it never installs them itself:

| File | What it does |
|---|---|
| [`contrib/lumen-panel-sync.service`](../contrib/lumen-panel-sync.service) | runs `python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp` once, with low priority, a 200 MB memory limit and a sandbox in which only `theme/`, `cache/twig/` and `/root/backups/lumen-panel` are writable and there is no network |
| [`contrib/lumen-panel-sync.timer`](../contrib/lumen-panel-sync.timer) | starts the service every day at 05:30 (plus up to 15 minutes of random delay) and catches up a missed run after a reboot |

Both files assume the checkout in `/opt/lumen-panel` and the panel in `/home/keyhelp/www/keyhelp`.
To install them:

```bash
sudo install -d -m 700 /root/backups/lumen-panel
sudo install -m 644 contrib/lumen-panel-sync.service contrib/lumen-panel-sync.timer /etc/systemd/system/
sudo systemctl edit --full lumen-panel-sync.service   # only if your paths differ
sudo systemctl daemon-reload
sudo systemctl enable --now lumen-panel-sync.timer
```

Check it:

```bash
systemctl list-timers lumen-panel-sync.timer
sudo systemctl start lumen-panel-sync.service
journalctl -u lumen-panel-sync.service -n 20 --no-pager
```

A run where nothing changed logs `up to date (...)`. A failed rebuild leaves the previous build
active and marks the service as failed, so it shows in `systemctl --failed`; the
[runbook](runbook.md#failure-lumen-panel-syncservice-failed) has the steps.

To remove the timer:

```bash
sudo systemctl disable --now lumen-panel-sync.timer
sudo rm /etc/systemd/system/lumen-panel-sync.service /etc/systemd/system/lumen-panel-sync.timer
sudo systemctl daemon-reload
```

## When the patch set does not fit the new templates

If `sync` stops with "the patch set does not fit this KeyHelp version", nothing was changed: the
panel keeps running on the previous Lumen build, whose templates come from the older default
theme. If a page misbehaves until the fix is in, select the default theme under
**Configuration -> Theme**. Then either update lumen-panel (a release for the new KeyHelp version
may already exist) or adjust the anchors in `patches/*.json` to the new templates (each anchor
must occur exactly once), run the tests and install again; see
[Troubleshooting](troubleshooting.md).
