# Installation

lumen-panel uses only what KeyHelp itself provides for changing the look of the panel: theme
folders and the White Label settings. Keyweb AG describes both on its
[overview of all functions](https://www.keyweb.de/en/keyhelp/keyhelp/overview-of-all-functions):
"With the white-label function, you can tailor the server hosting tool to your design ideas: Use
your own logo and adapt styles and functions to your own wishes and needs. In addition, you can
also develop your own themes." There are two routes:

| | Route A: the Lumen theme | Route B: White Label only |
|---|---|---|
| What you get | the stylesheet (light and dark, left to right and right to left), the command palette (Ctrl+K), the Luminare logo in the panel, the login page design | the stylesheet (light and dark, both text directions) and your own logos |
| What you do not get | (all of the above is included) | the command palette, the Sora font, the template patches (Luminare logo, the full login page design) |
| What it needs | a main administrator account, a root shell on the panel server, Python 3.10 or later, git, the built assets | a main administrator account, a browser and one built file |
| What it changes | `theme/lumen`, the compiled Lumen templates in the Twig cache, backups in `/root/backups/lumen-panel` | the Additional CSS setting on the White Label page (and the logo fields, if you upload logos) |
| After a KeyHelp update | `sync` rebuilds the copied templates, by hand or with the optional units | nothing to rebuild |
| Undo | select the default theme (one click) | empty the field (and remove the logos) and save |

Most of this guide is route A. [Route B](#route-b-white-label-only) comes at the end, together with
a [list of the panel labels](#panel-labels-in-english-and-german) in English and German.

KeyHelp is a registered trademark of Keyweb AG. lumen-panel is not affiliated with or endorsed by
Keyweb AG. Every official KeyHelp page this guide relies on is listed, with the date it was
checked and what it says, in [Official KeyHelp resources](keyhelp-resources.md).

**Status of testing (2026-10-21).** Route A: `build`, `verify` and the dry run ran against
KeyHelp 26.1.1 (default theme 26.1.1) on Ubuntu 24.04 with Python 3.12, read-only, with
placeholder assets; `install`, `rollback`, `sync`, `uninstall`, `hold` and `release`, including
interrupted and parallel runs, are covered by the test suite on a fake panel tree. CI builds the
assets, runs the 41 command palette tests and builds and verifies a theme from those assets on
every commit. `install` ran on the live KeyHelp 26.1.1 panel on 2026-10-21; the theme has not been
selected yet, so activation, rollback and uninstall on a live panel are still to come. Route B has
not been tried on a live panel yet.

## Contents

- Route A: [Requirements](#requirements) · [Get the code](#get-the-code) ·
  [Get the built assets](#get-the-built-assets) · [Dry run](#dry-run) · [Install](#install) ·
  [What the install changes](#what-the-install-changes) ·
  [Check the installed theme](#check-the-installed-theme) ·
  [Activate Lumen in the panel](#activate-lumen-in-the-panel) ·
  [Check it in the browser](#check-it-in-the-browser) ·
  [Switch back, roll back or uninstall](#switch-back-roll-back-or-uninstall) ·
  [Rebuild automatically (optional)](#rebuild-automatically-optional) ·
  [Update lumen-panel](#update-lumen-panel) · [After a KeyHelp update](#after-a-keyhelp-update)
- [Route B: White Label only](#route-b-white-label-only)
- [Panel labels in English and German](#panel-labels-in-english-and-german)

## Requirements

| Requirement | Details | How to check |
|---|---|---|
| KeyHelp | 26.1.1 tested (default theme `bulma` 26.1.1); 26.1.x supported; another version works when every patch anchor still fits, which the [dry run](#dry-run) checks. KeyHelp itself is installed as Keyweb describes under [Install KeyHelp](https://www.keyweb.de/en/keyhelp/keyhelp/#install). The default theme must be present and unmodified. | `grep '"version"' /home/keyhelp/www/keyhelp/theme/bulma/_settings.json` |
| Operating system | Ubuntu 24.04 tested; any system KeyHelp runs on (Keyweb lists Ubuntu LTS and Debian) | `grep PRETTY_NAME /etc/os-release` |
| Panel account | a main administrator. The panel's own help text says main administrators "can access license management and white label settings"; the Theme page is part of Configuration. | log in and open **Configuration** |
| Shell | root on the panel server, for example SSH and `sudo -i`. The install writes below the panel's web root and gives the files to `keyhelp:keyhelp`. | `id -u` prints `0` |
| Python | 3.10 or later, standard library only (Ubuntu 24.04 ships 3.12) | `python3 --version` |
| git | to fetch the code (not needed with the [release archive](#alternative-the-release-archive)) | `git --version`; install it with `apt install git` |
| Node.js | not needed on the server when you use the assets CI builds. Only to build the assets yourself, preferably on another machine: 22.22.2 or later (22.x), 24.15 or later, or 26. | |

The commands below assume a standard KeyHelp install, whose web root (with the `theme/` folder) is
`/home/keyhelp/www/keyhelp`, and the lumen-panel checkout in `/opt/lumen-panel`, where the optional
units in `contrib/` expect it. Run every command as root.

Before you start, read the [KeyHelp changelog](https://changelog.keyhelp.de/) entry for the
version you run, and note that Keyweb's knowledge base asks to make changes "primarily in the
configuration GUI", because KeyHelp can overwrite manual changes to the files it generates
([Configuration Files & Storage Paths](https://kb.keyhelp.de/article/configuration-files-storage-paths-119.html)).
lumen-panel keeps to that: it changes none of KeyHelp's files and adds its own theme folder, the
way Keyweb describes for own themes ("a sub-folder within the /theme/ directory",
[community forum, Keyweb AG, 2021](https://community.keyhelp.de/viewtopic.php?t=10363)). Selecting
the theme is done in the panel.

## Get the code

Clone the repository and check out the newest release tag:

```bash
git clone https://github.com/luminare-dev/lumen-panel.git /opt/lumen-panel
cd /opt/lumen-panel
git tag --list 'v*' --sort=-v:refname | head -n 1     # the newest release, for example v0.1.0
git checkout --quiet vX.Y.Z                           # that tag
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
```

The generator runs as root, so the checkout belongs to root and nobody else can write to it. Until
the first release is published, stay on `main` and skip the `git checkout`.

### Alternative: the release archive

Every release has a source archive, a `SHA256SUMS` file and, for releases made while the
repository is public, a build provenance attestation. The archive holds the same files as the tag:

```bash
V=X.Y.Z
cd /root
curl -fsSLO "https://github.com/luminare-dev/lumen-panel/releases/download/v$V/lumen-panel-$V.tar.gz"
curl -fsSLO "https://github.com/luminare-dev/lumen-panel/releases/download/v$V/SHA256SUMS"
sha256sum -c SHA256SUMS                                # lumen-panel-X.Y.Z.tar.gz: OK
gh attestation verify "lumen-panel-$V.tar.gz" --repo luminare-dev/lumen-panel   # optional, GitHub CLI
tar -xzf "lumen-panel-$V.tar.gz" -C /opt && mv "/opt/lumen-panel-$V" /opt/lumen-panel
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
```

Stop if `sha256sum -c` does not print `OK`.

## Get the built assets

The theme needs the built stylesheets, the command palette script, the font and the logo files in
`/opt/lumen-panel/dist/assets/`. They are not in git and not in the release archive. Take them
from CI, or build them yourself.

### From CI: the `theme-assets` artifact

CI builds every commit and keeps the built `dist/assets/` as the artifact `theme-assets` for 30
days. Use the artifact of exactly the commit you checked out, and check its SHA-256 digest: GitHub
records the digest of every artifact's zip file when it is uploaded and shows it next to the
artifact on the run page and as `digest` in its REST API
([GitHub changelog, 2025-03-18](https://github.blog/changelog/2025-03-18-github-actions-now-supports-a-digest-for-validating-your-artifacts-at-runtime/), [REST API reference](https://docs.github.com/en/rest/actions/artifacts)).

In the browser (signed in to GitHub): **Actions** → **ci** → the run of your commit
(`git -C /opt/lumen-panel rev-parse HEAD` prints it, or the commit of the release tag on GitHub) →
**Artifacts** → `theme-assets`. Note the digest shown there, download the zip, and compare it
with `sha256sum theme-assets.zip`.

With the GitHub CLI, on any machine where you ran `gh auth login`:

```bash
COMMIT=<the output of: git -C /opt/lumen-panel rev-parse HEAD>
# with the release archive instead of git: COMMIT=$(gh api repos/luminare-dev/lumen-panel/commits/vX.Y.Z --jq .sha)
gh run list --repo luminare-dev/lumen-panel --workflow ci.yml --commit "$COMMIT" --status success \
  --json databaseId --jq '.[0].databaseId'
RUN=<the run id it printed>
gh api "repos/luminare-dev/lumen-panel/actions/runs/$RUN/artifacts" \
  --jq '.artifacts[] | select(.name == "theme-assets") | "\(.id) \(.digest)"'
# prints: <artifact id> sha256:<64 hex digits>
gh api "repos/luminare-dev/lumen-panel/actions/artifacts/<artifact id>/zip" > theme-assets.zip
echo "<64 hex digits>  theme-assets.zip" | sha256sum -c -   # theme-assets.zip: OK
```

Copy the zip to the server (for example `scp theme-assets.zip root@<panel host>:/root/`) and
unpack it there with Python's own zip module, so no `unzip` package is needed:

```bash
cd /opt/lumen-panel
rm -rf dist/assets && mkdir -p dist/assets
python3 -m zipfile -e /root/theme-assets.zip dist/assets/
head -c 30 dist/assets/lumen.css; echo                  # /*! lumen-panel X.Y.Z | MIT
(cd generator && python3 -m lumen_panel version)        # X.Y.Z, the same version
chown -R root:root dist && chmod -R go-w dist
```

The version in the first line of `lumen.css` must match the generator's version (between two
releases both show the last release). The digest is the real check; the version only catches a
zip from another release. The generator also refuses an assets folder with a missing file, or
with any file the theme does not use.

After 30 days the artifact is gone; build the assets yourself then.

### Build them yourself

On a workstation with Node.js (versions in [Requirements](#requirements)), from the same tag:

```bash
git clone https://github.com/luminare-dev/lumen-panel.git && cd lumen-panel
git checkout --quiet vX.Y.Z
npm ci --ignore-scripts
npm run build:css && npm run build:island          # writes dist/assets/ (the gallery is not needed)
tar -C dist -cf - assets | ssh root@<panel host> \
  'rm -rf /opt/lumen-panel/dist/assets && mkdir -p /opt/lumen-panel/dist && tar -C /opt/lumen-panel/dist -xf - && chown -R root:root /opt/lumen-panel/dist && chmod -R go-w /opt/lumen-panel/dist'
```

Building on the panel server itself is possible, but on a small server that also runs mail and
ClamAV an unbounded `npm` run can push other programs out of memory. Only with enough free memory,
and only with these limits (the commands refuse to start with less than 650 MB available and cap
the build at 450 MB):

```bash
cd /opt/lumen-panel
if awk '/MemAvailable/ {exit !($2>=665600)}' /proc/meminfo; then
  systemd-run --scope --quiet --collect -p MemoryMax=450M -p MemorySwapMax=0 \
    env NODE_OPTIONS=--max-old-space-size=320 nice -n 19 npm ci --ignore-scripts &&
  systemd-run --scope --quiet --collect -p MemoryMax=450M -p MemorySwapMax=0 \
    env NODE_OPTIONS=--max-old-space-size=320 nice -n 19 npm run build:css &&
  systemd-run --scope --quiet --collect -p MemoryMax=450M -p MemorySwapMax=0 \
    env NODE_OPTIONS=--max-old-space-size=320 nice -n 19 npm run build:island
else
  echo 'less than 650 MB available: use the CI artifact or build on another machine'
fi
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
```

## Dry run

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
```

The dry run builds the theme in a temporary folder (removed afterwards), verifies it against the
installed default theme, and checks the owner, write access to `theme/` and the backup folder. It
writes nothing below the panel's web root. A good run prints, among other lines:

```text
dry run: build and verify passed (default theme 26.1.1, 7 patches, assets <hash>)
dry run: would build in /home/keyhelp/www/keyhelp/theme/.lumen-staging-<timestamp> and swap it in at /home/keyhelp/www/keyhelp/theme/lumen
dry run: would set owner keyhelp:keyhelp, folders 755, files 644; nothing was written
```

and exits 0. Stop on any other result:

- `error: the patch set does not fit this KeyHelp version; nothing was installed`, followed by one
  line per patch that failed (exit 1): this KeyHelp version changed a template at a place the
  patch set relies on. See [After a KeyHelp update](#after-a-keyhelp-update).
- `assets incomplete` or `files the theme does not use` (exit 2): the assets folder is incomplete
  or holds other files; get it again ([Get the built assets](#get-the-built-assets)).

Every exit code is listed in [Configuration](configuration.md#exit-codes).

## Install

```bash
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp
```

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
`failed-staging`, never left in `theme/`. The output ends with the undo commands and, on a first
install, `Next: KeyHelp -> Configuration -> Appearance -> Theme -> select 'Lumen' and save.`

The install does not select the theme: until you do, the panel keeps showing the theme it showed
before, and Lumen is only listed on the Theme page.

## What the install changes

| Path | Change |
|---|---|
| `/home/keyhelp/www/keyhelp/theme/lumen/` | created, or replaced in one atomic rename. Holds `templates/` (the patched copy of the default templates), `assets/` (Lumen's own files), `_settings.json` (what the Theme page lists), `_screenshot.png`, the build record `_lumen_build.json` and `LUMEN-README.txt`. Owner `keyhelp:keyhelp`, folders 755, files 644. |
| `theme/.lumen-staging-<timestamp>/`, `theme/.lumen-previous-<timestamp>/` | exist only while a run works; a stopped run's folders are moved to the backups by the next run. |
| `/home/keyhelp/www/keyhelp/cache/twig/<2 hex>/<hex>.php` | only the compiled templates whose recorded source lies below `theme/lumen/templates/` are moved to the backup folder (`twig-cache/`, and `twig-cache-late/` for the second pass). Every other entry stays. A first install finds none. |
| `/root/backups/lumen-panel/` | created with mode 700. Holds the run lock `.lock`, the hold file `HOLD` (after a `rollback` or `hold`) and one folder per run, named by its UTC time (for example `20261021T041348050556Z`), with `ROLLBACK.txt` and, as the run needs them, `lumen/` (the previous build), `twig-cache/`, `twig-cache-late/`, `stale/` and `failed-staging/`. Nothing in it is ever deleted; remove old folders yourself. |
| not changed | the default theme `theme/bulma` (only read), KeyHelp's database and settings (the selected theme, the White Label settings), every other file of the panel, the system (no packages; units only if you install them). |

## Check the installed theme

Before you select the theme for all accounts, check the installed folder:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp
ls -ld /home/keyhelp/www/keyhelp/theme/lumen          # owner keyhelp keyhelp
```

`verify` prints one `ok:` line per check (settings, templates, contents, patches, twig syntax,
assets, screenshot) and exits 0; `check-update` prints `up to date (default theme 26.1.1,
lumen-panel X.Y.Z)` and exits 0. Go on only when both commands exit 0.

## Activate Lumen in the panel

1. Log in to the panel as a main administrator.
2. Open **Configuration**, then **Theme** in the **Appearance** group. The page lists every theme
   folder with its preview, **Description**, **Version**, **Author** and **Website**; its help text
   reads "Change the theme for all accounts on this server."
3. Select **Lumen**.
4. Below it, choose the **Default design mode**: **Default** (light) or **Dark mode**. Every user
   can still switch with **Enable dark mode** or **Disable dark mode** in the user menu, and Lumen
   follows that switch. Keyweb lists dark mode among the features of KeyHelp Pro on its
   [product page](https://www.keyweb.de/en/keyhelp/keyhelp/); where the panel shows no dark mode,
   Lumen shows its light design.
5. Click **Save**. KeyHelp clears its template cache when the theme changes (changelog of KeyHelp
   19.3, "Template cache now gets deleted when switching between themes").

The Theme page also notes that White Label settings may need an update to work with the selected
theme. White Label CSS loads after Lumen's stylesheet and wins, so review **Configuration** →
**Appearance** → **White Label** → **Additional CSS** if colours look wrong. A White Label logo for
the internal or external area also wins over the Luminare logo.

## Check it in the browser

Reload once without the cache (Ctrl+Shift+R):

- the login page shows the Luminare logo (or your White Label logo for the external area);
- every page after login loads `/theme/lumen/assets/lumen.css?v=<hash>`, or its `-dark` or `-rtl`
  variant (developer tools, Network tab), where `<hash>` is the assets hash the install printed;
- Ctrl+K (Cmd+K on a Mac), or the search button in the header, opens the command palette.

## Switch back, roll back or uninstall

### Switch back at once

**Configuration** → **Appearance** → **Theme** → select **Default Theme** → **Save**. Nothing on
disk changes, so you can select **Lumen** again at any time. `sync` and the optional units keep
the installed build current in the meantime.

### If the panel cannot show the Theme page

Move the Lumen folder out of the panel; the command does not ask the panel first:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --yes
```

Keyweb's fix for a theme that breaks the panel has two steps: remove the theme's folder, and set
`default_theme` (table `settings`, category `general`) back to `bulma` in KeyHelp's database
([community forum, Keyweb AG, 2021](https://community.keyhelp.de/viewtopic.php?t=10272)). The
command above does the first step without deleting anything. Whether the panel falls back to the
default theme without the second step has not been tested; if pages still fail, do the second
step as Keyweb describes.

### Roll back to the previous build

Every install writes its undo command to `ROLLBACK.txt` in its backup folder; each
`python3 -m lumen_panel` command in it starts with `cd` into the generator folder, so it works
from any folder. After a first install there is no previous build, and the undo is the
[uninstall](#uninstall) below; after every later install it is a rollback:

```bash
cd /opt/lumen-panel/generator
cat /root/backups/lumen-panel/<timestamp>/ROLLBACK.txt
python3 -m lumen_panel rollback --keyhelp /home/keyhelp/www/keyhelp --from /root/backups/lumen-panel/<timestamp>
```

The backup is copied, not moved. A rollback sets a hold, so `sync` and the units do not rebuild
the version you just left; the next `install` (or `release`) ends the hold.

### Uninstall

1. In the panel: **Configuration** → **Appearance** → **Theme**, select **Default Theme** and
   save.
2. Move the theme folder to the backups:

   ```bash
   cd /opt/lumen-panel/generator
   python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --panel-url https://<your panel>/
   ```

With `--panel-url`, the command loads the login page once and refuses (exit 4) while it still
loads the Lumen stylesheet, and exits 5 when the page cannot be reached or shows neither
stylesheet (then re-run with `--yes` after step 1); add `--insecure` for a self-signed panel
certificate. Without it, run the command with `--yes` after step 1 (it exits 5 otherwise). The
removed folder and its compiled templates stay in `/root/backups/lumen-panel/<timestamp>/`.

To remove everything afterwards: the optional units, if installed
([Rebuild automatically](#rebuild-automatically-optional)), then `/opt/lumen-panel` and, once you
no longer need the backups, `/root/backups/lumen-panel`.

## Rebuild automatically (optional)

lumen-panel ships three example systemd units in `contrib/` and never installs them itself. They
are opt-in:

- `lumen-panel-sync.service` waits 120 seconds (a panel update may still be writing), then runs
  `python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp` once, with low priority, a
  200 MB memory limit and a sandbox (only `theme/`, `cache/twig/` and `/root/backups/lumen-panel`
  are writable, `theme/bulma` stays read-only, no network). Exit code 75 starts it again 10
  minutes later.
- `lumen-panel-sync.path` starts the service when `theme/bulma/_settings.json` changes, which every
  panel update does.
- `lumen-panel-sync.timer` starts the service every day at 05:30 (plus up to 15 minutes of random
  delay) and catches up a run missed while the server was off.

`sync` rebuilds only when the default theme, the generator, the assets or the patch set changed;
otherwise it logs `up to date (...)`. The units assume `/opt/lumen-panel` and
`/home/keyhelp/www/keyhelp`; if your paths differ, adapt the copies in `/etc/systemd/system/`
with `systemctl edit --full` before enabling them. Install the units:

```bash
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
install -d -m 700 /root/backups/lumen-panel
cd /opt/lumen-panel
install -m 644 contrib/lumen-panel-sync.service contrib/lumen-panel-sync.path \
  contrib/lumen-panel-sync.timer /etc/systemd/system/
# systemctl edit --full lumen-panel-sync.service   # only if your paths differ (and the .path unit)
systemctl daemon-reload
systemctl enable --now lumen-panel-sync.path
systemctl enable --now lumen-panel-sync.timer
```

Check them:

```bash
systemctl status lumen-panel-sync.path --no-pager
systemctl list-timers lumen-panel-sync.timer
systemctl start lumen-panel-sync.service          # takes a little over 2 minutes (the wait)
journalctl -u lumen-panel-sync.service -n 20 --no-pager
```

A failed rebuild leaves the previous build active and marks the service as failed, so it shows in
`systemctl --failed`. Remove the units:

```bash
systemctl disable --now lumen-panel-sync.path lumen-panel-sync.timer
rm /etc/systemd/system/lumen-panel-sync.service /etc/systemd/system/lumen-panel-sync.path \
  /etc/systemd/system/lumen-panel-sync.timer
systemctl daemon-reload
```

More about the units, the sandbox and holds: [Keeping the theme current](update.md).

## Update lumen-panel

Read the [changelog](../CHANGELOG.md) entries between your version and the new one first
(breaking changes are listed there), then:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel hold                  # the units do not rebuild halfway through
cd /opt/lumen-panel
git fetch --tags
git checkout --quiet vX.Y.Z                  # the new release
```

Then replace `dist/assets/` with the assets of the new tag ([Get the built assets](#get-the-built-assets)),
and continue:

```bash
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
cd /opt/lumen-panel/generator
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp     # also ends the hold
```

If the dry run fails, nothing changed and the hold is still set. Either fix the cause and run
`install`, or go back to the previous tag (`git checkout --quiet vOLD` and that tag's assets) and
run `python3 -m lumen_panel release`. Do not leave the hold set: while it is, `sync` does not
follow KeyHelp updates.

Then [check the installed theme](#check-the-installed-theme) and
[check it in the browser](#check-it-in-the-browser). With the release archive instead of git,
unpack the new archive next to the old folder, put the new tag's assets into its `dist/assets/`,
swap the two folders and run the same commands. See also [Upgrading lumen-panel](upgrade.md).

## After a KeyHelp update

A KeyHelp update replaces the default theme (`theme/bulma`) and keeps theme folders of their own:
"Custom themes are now transferred to the new KeyHelp version during panel update process"
(changelog of KeyHelp 19.2), and Keyweb adds that this needs a folder name of its own
([community forum, Keyweb AG, 2019](https://community.keyhelp.de/viewtopic.php?t=8502)). So
`theme/lumen` survives, but its templates are copies from the previous default theme until
lumen-panel rebuilds them. When the panel updates itself with its maintenance task **Update
control panel** ("Keeps the control panel up-to-date and installs newer versions as soon as they
are released."), an update can come at any time; then the
[optional units](#rebuild-automatically-optional) are the way to keep Lumen in step.

1. **Read the changelog first:** <https://changelog.keyhelp.de/>, every version between yours and
   the new one. Entries about the template system or engine, themes, layouts or White Label are
   the ones that can affect Lumen (KeyHelp 25.1, for example, "Performed a comprehensive rework of
   the template engine and all associated UI templates"). If you see such entries, select
   **Default Theme** before the update and select **Lumen** again after step 4.
2. Update KeyHelp as usual. KeyHelp keeps a backup of itself before a panel update in
   `/home/keyhelp/keyhelp.backup/` ([knowledge base](https://kb.keyhelp.de/article/configuration-files-storage-paths-119.html)).
3. See what changed for Lumen, and whether the patch set still fits, without changing anything:

   ```bash
   cd /opt/lumen-panel/generator
   python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp   # 0 current, 10 rebuild needed
   python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
   ```

4. Rebuild (only when needed) and check:

   ```bash
   python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp
   python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
   ```

   With the units installed, the `.path` unit starts the same `sync` minutes after the update.

**When a patch anchor no longer fits.** Each patch inserts a few lines next to an anchor that must
occur exactly once in a default template. If the new templates changed at that place, the build
stops with `the patch set does not fit this KeyHelp version; nothing was installed` and names every
failed patch, for example `10-base-stylesheet.json [base-stylesheet]: anchor not found in
layout/base.twig`. Nothing is written, so the previous Lumen build stays active: its templates come
from the older default theme, while the panel's code and the `/theme/bulma/` stylesheets and
scripts are already new. That can break pages. Check the panel, and if a page misbehaves, select
**Default Theme** until the fix is in. Then update lumen-panel (a release for the new KeyHelp
version may exist) or adjust the anchors in `patches/*.json`, run the tests and install again
([Keeping the theme current](update.md#when-the-patch-set-does-not-fit-the-new-templates),
[Troubleshooting](troubleshooting.md)).

## Route B: White Label only

The panel's White Label page (**Configuration** → **Appearance** → **White Label**, main
administrators only) takes additional CSS, additional JavaScript, logos, a favicon, a page title
and a footer. It needs no shell and no theme folder, and it lives in the panel's settings rather
than in files, so there is no template copy to rebuild after a KeyHelp update. The KeyHelp FAQ
series in Keyweb's [tutorials](https://www.keyweb.de/en/support/learn-more/tutorials#keyhelp)
has an entry "Customize with white label".

### How the panel inserts White Label CSS and JavaScript

From a read-only look at the base layout of the 26.1.1 default theme (described, not copied): the
**Additional CSS** is printed inline, as a `<style>` element at the end of `<head>`, after the
default theme's stylesheet and after the page's own CSS. The **Additional JavaScript** is printed
inline, as a `<script>` element at the very end of `<body>`, after the panel's own scripts. Every
page is built on that base layout: the login and password pages, every page after login and the
popup windows. So White Label CSS applies everywhere and in both design modes (`<body>` carries
`dark-mode` or `default-mode`), and it is part of every HTML page instead of a file the browser
caches. With the Lumen theme, Lumen's stylesheet loads before the page's CSS and the White Label
CSS, so White Label CSS still overrides it.

### What works with White Label alone

| Part | With White Label alone | Why |
|---|---|---|
| Stylesheet | works: paste `lumen-rtl.css` | the light build plus the right-to-left additions, which apply only on right-to-left pages; dark mode works because the stylesheet carries its dark tokens for `body.dark-mode` |
| Logos | work: your own files in the White Label logo fields | the panel shows a White Label logo instead of the KeyHelp logo on its own |
| Sora font | does not load; the system font is used | the stylesheet names the font file by a relative path, which in an inline style resolves against the panel page and fails (one failed request per page) |
| Login page design | partly: the general rules apply | the login rules need the `lumen-extern` class that the theme's template patch adds |
| Command palette | not available | the theme loads it as one cached, deferred file on pages after login only; White Label JavaScript is printed inline into every page, login and popups included, and lumen-panel does not build or test the palette for that |
| Template patches | not available | White Label settings cannot change templates: no stylesheet chosen per user mode and text direction, no hook classes, no logo replacement by the theme |

The trade-offs: route B is the lighter path and uses the White Label settings only (no files on
the server, no rebuild after KeyHelp updates, no root shell). Route A gives the whole design, the
command palette and per-variant stylesheets the browser caches, and in return needs a theme
folder that `sync` keeps in step with KeyHelp, and a root shell to set it up.

### Set up route B

1. Get `lumen-rtl.css`: it is in the `theme-assets` artifact, or in `dist/assets/` after a build
   ([Get the built assets](#get-the-built-assets); check the digest the same way). You only need
   this one file, on the machine you use the browser on. It is about 46 KB, minified.
2. Log in as a main administrator and open **Configuration** → **Appearance** → **White Label**.
3. The overview lists **All languages** and one row per language. Edit **All languages**: per the
   page's help, these settings apply to all accounts regardless of their language and can be
   overwritten by language-specific settings, so check that no language row has CSS of its own.
4. Paste the whole content of `lumen-rtl.css` into **Additional CSS** (the field's help: "You can
   define your own CSS styles and override the current design."). Leave **Additional
   JavaScript** as it is.
5. Click **Preview on this page** below **Additional CSS** to see the result before you save.
6. Optional: upload your own logos under **Logo for internal area** (header after login and in
   popups) and **Logo for external area** (login and password pages), each with a file for the
   default mode and one for dark mode where the form has both; the page advises SVG. Never
   upload a changed KeyHelp logo: the page itself notes that KeyHelp is a registered trademark of
   Keyweb AG that may not be presented as your own, and Keyweb asks not to change the KeyHelp logo
   ([community forum, Keyweb AG, 2021](https://community.keyhelp.de/viewtopic.php?t=10363)). The
   Luminare logo files in `dist/assets/brand/` are not licensed for reuse ([NOTICE](../NOTICE)).
7. **Save**, then reload a panel page without the cache (Ctrl+Shift+R). After saving, open
   **All languages** again and check that **Additional CSS** still ends with the last rule of
   `lumen-rtl.css` (a field of this size has not been tried yet).

Use one route at a time: with route B, keep **Default Theme** selected under
**Configuration** → **Appearance** → **Theme**. With the Lumen theme selected, a pasted copy of
Lumen's CSS would load a second time, last, and an older copy would override the newer theme.

To undo route B, edit **All languages** again, empty **Additional CSS** (and use **Remove image**
for the logos) and save. **Reset all settings** on the overview resets every White Label setting,
not only these. After a lumen-panel update, paste the new file. After a KeyHelp update nothing
needs a rebuild; check the pages, because changed markup can make single rules stop matching.

## Panel labels in English and German

The labels as KeyHelp 26.1.1 shows them (from its message catalogues):

| English | German |
|---|---|
| Configuration → Appearance → Theme | Konfiguration → Erscheinungsbild → Theme |
| Default design mode: Default, Dark mode | Standard Design-Modus: Standard, Dark-Mode |
| Default Theme (the name the default theme `bulma` gives itself in its `_settings.json`) | Default Theme |
| Save | Speichern |
| Enable dark mode, Disable dark mode (user menu) | Dark-Mode aktivieren, Dark-Mode deaktivieren |
| Configuration → Appearance → White Label | Konfiguration → Erscheinungsbild → White-Label |
| All languages | Alle Sprachen |
| Additional CSS, Additional JavaScript | Zusätzliches CSS, Zusätzliches JavaScript |
| Preview on this page (the button below Additional CSS) | Vorschau auf dieser Seite |
| Logo for internal area, Logo for external area | Logo für den internen Bereich, Logo für den externen Bereich |
| Remove image, Reset all settings | Bild entfernen, Alle Einstellungen zurücksetzen |
| Maintenance Intervals → Update control panel | Wartungsintervalle → Control Panel aktualisieren |
