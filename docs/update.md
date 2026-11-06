# Keeping the theme current after a KeyHelp update

A KeyHelp update replaces the default theme (`theme/bulma`) but leaves `theme/lumen` and
`theme/lumen-dark` alone, so their copied templates go stale. The generator notices this and
rebuilds from the new default theme already on the server; no Node.js is needed. Read the
[KeyHelp changelog](https://changelog.keyhelp.de/) before each update.

For new versions of lumen-panel itself, see [Upgrading lumen-panel](upgrade.md).

## Check and rebuild by hand

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel check-update --variant all --keyhelp /home/keyhelp/www/keyhelp   # 0 = current, 10 = rebuild needed
python3 -m lumen_panel sync --variant all --keyhelp /home/keyhelp/www/keyhelp           # rebuild what needs it
```

A rebuild is due when the default theme, the generator version, the built assets or the patch set
differ from the theme's build record (`_lumen_build.json`). `sync` then runs `install` for that
theme; themes that are not installed are skipped. Exit 75 means another run was active or the
default theme changed mid-copy: try again a few minutes later.

## Rebuild automatically (optional units)

| File | What it does |
|---|---|
| [`contrib/lumen-panel-sync.service`](../contrib/lumen-panel-sync.service) | waits 120 s, then runs `python3 -m lumen_panel sync --variant all` in a sandbox with a 200 MB memory limit; exit 75 retries after 10 minutes |
| [`contrib/lumen-panel-sync.path`](../contrib/lumen-panel-sync.path) | starts the service when `theme/bulma/_settings.json` changes (every panel update) |
| [`contrib/lumen-panel-sync.timer`](../contrib/lumen-panel-sync.timer) | daily fallback at 05:30, catches up after a reboot |

The units assume `/opt/lumen-panel` and `/home/keyhelp/www/keyhelp`; adapt them with
`systemctl edit --full` if your paths differ.

```bash
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
install -d -m 700 /root/backups/lumen-panel
cd /opt/lumen-panel
install -m 644 contrib/lumen-panel-sync.service contrib/lumen-panel-sync.path \
  contrib/lumen-panel-sync.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now lumen-panel-sync.path
systemctl enable --now lumen-panel-sync.timer
```

Check with `systemctl list-timers lumen-panel-sync.timer` and
`journalctl -u lumen-panel-sync.service -n 20`. A failed rebuild leaves the previous build active
and shows in `systemctl --failed` (see the [runbook](runbook.md#failure-lumen-panel-syncservice-failed)).

To remove them:

```bash
systemctl disable --now lumen-panel-sync.path lumen-panel-sync.timer
rm /etc/systemd/system/lumen-panel-sync.{service,path,timer}
systemctl daemon-reload
```

## Holding the theme

`rollback` sets a hold, and `sync` leaves a held theme alone. You can also hold one by hand:

```bash
python3 -m lumen_panel hold                 # or --variant lumen-dark / all
python3 -m lumen_panel release              # let sync rebuild it again
```

`install` also ends the hold.

## When the patch set does not fit the new templates

`sync` stops with "the patch set does not fit this KeyHelp version" and changes nothing. The old
build keeps running against the new panel, which can break pages, so check the panel and select
**Default Theme** if needed. Then update lumen-panel, or fix the anchors in `patches/*.json` (and
`patches/lumen-dark/*.json`; each anchor must occur exactly once), run the tests and install
again. See [Troubleshooting](troubleshooting.md).
