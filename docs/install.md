# Installation

The theme is built on the panel server itself: the generator reads the installed default theme,
applies the patch set to a copy of its templates and adds the Lumen assets. Nothing of KeyHelp is
downloaded or shipped with this repository.

Status of testing (2026-10-21): `build` and `verify` ran against KeyHelp 26.1.1 on Ubuntu 24.04
(Python 3.12) with placeholder assets; `install`, `rollback`, `sync`, `uninstall`, `hold` and
`release`, including interrupted and parallel runs, are covered by the test suite on a fake panel
tree. The asset build (`npm run build`) and the command palette's unit tests have not run yet, and
a first install on a live panel is still to come.

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| KeyHelp | 26.1.x | the default theme (`theme/bulma`) must be present and unmodified |
| Python | 3.10 or later | standard library only; runs the generator |
| Node.js and npm | Node.js 22.22.2 or later (22.x), 24.15 or later, or 26 | only to build the assets (`dist/assets`); can run on another machine |
| Shell access | root | the install writes `theme/lumen` and sets the owner `keyhelp:keyhelp` |

The generator itself is Python with the standard library only and needs no limit. The asset
build (Node.js) is the only step that needs real memory.

## Install

Build the assets on another machine if you can (a workstation or CI), and copy `dist/assets/`
to `/opt/lumen-panel/dist/assets/` on the server. On a small server that also runs mail and
ClamAV, an unbounded `npm` run can push other services out of memory; if you build on the server,
use the commands below, which refuse to start with less than 650 MB available and cap the build
at 450 MB.

```bash
sudo git clone https://github.com/luminare-dev/lumen-panel.git /opt/lumen-panel
cd /opt/lumen-panel
# skip this block if you copied a dist/assets/ built elsewhere
if awk '/MemAvailable/ {exit !($2>=665600)}' /proc/meminfo; then
  sudo systemd-run --scope --quiet --collect -p MemoryMax=450M -p MemorySwapMax=0 \
    env NODE_OPTIONS=--max-old-space-size=320 nice -n 19 npm ci --ignore-scripts &&
  sudo systemd-run --scope --quiet --collect -p MemoryMax=450M -p MemorySwapMax=0 \
    env NODE_OPTIONS=--max-old-space-size=320 nice -n 19 npm run build
else
  echo 'less than 650 MB available: build dist/assets/ elsewhere and copy it here'
fi
sudo chown -R root:root /opt/lumen-panel && sudo chmod -R go-w /opt/lumen-panel
cd /opt/lumen-panel/generator
sudo python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
sudo python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp
```

The generator runs as root, so the checkout belongs to root and nobody else can write to it.
`/opt/lumen-panel` is also where the optional units in `contrib/` expect it.

Then, in the panel: **Configuration -> Theme**, select **Lumen** and save. Every user keeps their
own light or dark mode (user menu).

What `install` does, in this order:

1. takes the run lock (`/root/backups/lumen-panel/.lock`; a second run exits 75), creates the
   backup folder `/root/backups/lumen-panel/<timestamp>/` and moves any `theme/.lumen-*` folder an
   interrupted run left behind into its `stale/` folder;
2. builds the theme in `theme/.lumen-staging-<timestamp>` (the default theme is only read; if it
   changes while it is copied, the build stops and installs nothing);
3. verifies it: every default template has a counterpart with the right content (byte for byte,
   patched files included), every patch is present once, the patched templates pass the Twig
   check and every referenced Lumen file exists;
4. sets folders to 755, files to 644 and the owner to `keyhelp:keyhelp`;
5. swaps it in at `theme/lumen` with one atomic rename; the replaced `theme/lumen` is parked with
   its `_settings.json` renamed at once, so the panel never lists it as a second theme;
6. moves the compiled Twig templates of the old Lumen build (only those) into the backup folder,
   writes the command that undoes the change to `ROLLBACK.txt` there, moves the parked build to
   `/root/backups/lumen-panel/<timestamp>/lumen` (nothing is deleted) and looks at the Twig cache
   once more two seconds later.

A build that fails or is stopped (Ctrl+C, `SIGTERM`) is moved to the backup folder as
`failed-staging`, never left in `theme/`.

If a patch does not fit (after a KeyHelp update), the build stops before anything changes and
lists every patch that failed; see [Troubleshooting](troubleshooting.md).

After every KeyHelp update, rebuild with `sync`, by hand or from the optional units in
`contrib/`, which start it when the default theme changes and once a day:
[Keeping the theme current after a KeyHelp update](update.md).

## Verify the release download

Every release has a `SHA256SUMS` file and a build provenance attestation:

```bash
sha256sum -c SHA256SUMS
gh attestation verify <archive>.tar.gz --repo luminare-dev/lumen-panel
```

## Check that it works

```bash
cd generator
sudo python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
sudo python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp
```

`verify` prints one `ok:` line per check (settings, templates, patches, twig syntax, assets,
screenshot) and exits 0; `check-update` prints `up to date (...)` and exits 0. In the browser, the
login page shows the Luminare logo, and on any page after login Ctrl+K (Cmd+K on a Mac) opens the
command palette.

## Uninstall

1. In the panel: **Configuration -> Theme**, select the default theme and save.
2. Move the theme folder to the backups:

```bash
cd generator
sudo python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --panel-url https://<your panel>/
```

With `--panel-url`, the command loads the login page once and refuses while it still references
the Lumen stylesheet. Without it, run it with `--yes` after step 1. The removed folder stays in
`/root/backups/lumen-panel/<timestamp>/lumen`; delete that folder yourself when you no longer need
it.
