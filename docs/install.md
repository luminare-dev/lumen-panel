# Installation

lumen-panel uses only what KeyHelp itself provides for changing the look of the panel: theme
folders and the White Label settings. Keyweb AG describes both on its
[overview of all functions](https://www.keyweb.de/en/keyhelp/keyhelp/overview-of-all-functions):
"With the white-label function, you can tailor the server hosting tool to your design ideas: Use
your own logo and adapt styles and functions to your own wishes and needs. In addition, you can
also develop your own themes." There are two routes:

| | Route A: the themes Lumen and Lumen Dark | Route B: White Label only |
|---|---|---|
| What you get | Lumen (light, and dark where the panel has a dark mode) or Lumen Dark (always dark), or both to choose from; each with the stylesheet for both text directions, the command palette (Ctrl+K), the Luminare logo in the panel and the login page design | Lumen's stylesheet (light and dark, both text directions) and your own logos |
| What you do not get | (all of the above is included) | Lumen Dark, the command palette, the Sora font, the template patches (Luminare logo, the full login page design) |
| What it needs | a main administrator account, a root shell on the panel server, Python 3.10 or later, git, the built assets | a main administrator account, a browser and one built file |
| What it changes | `theme/lumen` and/or `theme/lumen-dark`, their compiled templates in the Twig cache, backups in `/root/backups/lumen-panel` | the Additional CSS setting on the White Label page (and the logo fields, if you upload logos) |
| After a KeyHelp update | `sync` rebuilds the copied templates, by hand or with the optional units | nothing to rebuild |
| Undo | select the default theme (one click) | empty the field (and remove the logos) and save |

Most of this guide is route A. [Route B](#route-b-white-label-only) comes at the end, together with
a [list of the panel labels](#panel-labels-in-english-and-german) in English and German.

## Two themes: Lumen and Lumen Dark

The generator builds two themes from the same default theme and the same assets. Install either,
or both and switch between them under **Configuration** → **Appearance** → **Theme**:

| | Lumen | Lumen Dark |
|---|---|---|
| Listed as | **Lumen** | **Lumen Dark** |
| Folder | `theme/lumen` | `theme/lumen-dark` |
| Generator option | `--variant lumen` (the default, may be left out) | `--variant lumen-dark` |
| Look | light; dark where the panel has a dark mode (part of KeyHelp Pro) and a user turns it on | always dark, for every account |
| Built on | the default theme's stylesheet the panel picks (light, or dark in its dark mode) | always the default theme's standard (light) stylesheet, with lumen-panel's own dark stylesheet on top |
| Logo | the lockup for light backgrounds, or for dark ones in dark mode | always the lockup for dark backgrounds |
| Backups | `/root/backups/lumen-panel/<timestamp>/` | `/root/backups/lumen-panel/lumen-dark/<timestamp>/` |

**Lumen Dark is not the dark mode of KeyHelp Pro.** Its dark design is lumen-panel's own
stylesheet on top of the panel's standard light stylesheet, the way any custom theme may restyle
the panel. It declares no dark mode (`has_dark_mode: false`). It does not enable or unlock the
panel's dark mode, has no dark-mode switch, and loads none of the default theme's dark
stylesheets or images: on a panel without Pro, the panel's own dark mode stays unavailable, and
Lumen Dark adds nothing that depends on Pro
([ADR 0011](adr/0011-lumen-dark-is-a-design-not-the-pro-dark-mode.md)). Its description on the
Theme page says the same.

A few things stay as the panel draws them for light pages, because no stylesheet reaches them: the
doughnut charts keep their white segment borders (white rings on the dark card), logos uploaded
under White Label are shown as they are (one made for light backgrounds sits on the dark header
and login box), and the rich text editor's editing area is a light sheet on purpose, so the
colours its toolbar applies stay readable and messages look as they will on white.

The two never share a folder, a backup folder, a run lock, a hold or a compiled template:
installing, updating, rolling back or removing one leaves the other as it is
([ADR 0012](adr/0012-theme-variants-share-the-build-and-nothing-else.md)). Every command below is
written for Lumen; add `--variant lumen-dark` for Lumen Dark (the sections say where).

KeyHelp is a registered trademark of Keyweb AG. lumen-panel is not affiliated with or endorsed by
Keyweb AG. Every official KeyHelp page this guide relies on is listed, with the date it was
checked and what it says, in [Official KeyHelp resources](keyhelp-resources.md).

**Status of testing (2026-10-21).** Route A: `build`, `verify` and the dry run ran against
KeyHelp 26.1.1 (default theme 26.1.1) on Ubuntu 24.04 with Python 3.12, read-only, with
placeholder assets, for both themes; `install`, `rollback`, `sync`, `uninstall`, `hold` and
`release`, including interrupted and parallel runs and both themes side by side, are covered by
the test suite on a fake panel tree. CI builds the assets, runs the 52 command palette tests and
builds and verifies both themes from those assets on every commit. Lumen was installed and
selected on the live KeyHelp 26.1.1 panel on 2026-10-21; Lumen Dark was installed next to it the
same day (`verify` passed, including the Pro boundary check). Route B has not been tried on a
live panel yet.

## Contents

- Route A: [Two themes](#two-themes-lumen-and-lumen-dark) · [Requirements](#requirements) ·
  [Get the code](#get-the-code) · [Get the built assets](#get-the-built-assets) ·
  [Dry run](#dry-run) · [Install](#install) ·
  [What the install changes](#what-the-install-changes) ·
  [Check the installed theme](#check-the-installed-theme) ·
  [Activate Lumen or Lumen Dark in the panel](#activate-lumen-or-lumen-dark-in-the-panel) ·
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
repository is public, signed build provenance (`lumen-panel-X.Y.Z.tar.gz.intoto.jsonl`, a Sigstore
bundle with a SLSA provenance statement). The archive holds the same files as the tag. Download
and check it:

```bash
V=X.Y.Z
cd /root
curl -fsSLO "https://github.com/luminare-dev/lumen-panel/releases/download/v$V/lumen-panel-$V.tar.gz"
curl -fsSLO "https://github.com/luminare-dev/lumen-panel/releases/download/v$V/SHA256SUMS"
sha256sum -c SHA256SUMS                                # lumen-panel-X.Y.Z.tar.gz: OK
```

Stop if `sha256sum -c` does not print `OK`. To also check where the archive came from, run the
commands from [Verify a release](#verify-a-release) now, in `/root`. Then unpack it in the same
shell:

```bash
tar -xzf "lumen-panel-$V.tar.gz" -C /opt && mv "/opt/lumen-panel-$V" /opt/lumen-panel
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
```

### Verify a release

`sha256sum -c SHA256SUMS` shows that the archive arrived complete and unchanged. The build
provenance shows that the release workflow of `luminare-dev/lumen-panel`
(`.github/workflows/reusable-release.yml`, started from the `main` branch) built it on GitHub
Actions: it is signed with a short-lived Sigstore certificate issued to that workflow and recorded
in the public Rekor transparency log. `--signer-workflow` and `--source-ref` make the commands
below require exactly that workflow and branch; with `--repo` alone, any workflow of the
repository on any branch would pass. The release workflow checks the provenance file the same way
before it publishes a release. Check it with the [GitHub CLI](https://cli.github.com/), in the
folder with the downloaded archive:

```bash
V=X.Y.Z
sha256sum -c SHA256SUMS                                # lumen-panel-X.Y.Z.tar.gz: OK
# Provenance stored on GitHub (needs `gh auth login`):
gh attestation verify "lumen-panel-$V.tar.gz" --repo luminare-dev/lumen-panel \
  --signer-workflow luminare-dev/lumen-panel/.github/workflows/reusable-release.yml --source-ref refs/heads/main
# Or the provenance file of the release (no login, no GitHub API; see below for what it cannot check):
curl -fsSLO "https://github.com/luminare-dev/lumen-panel/releases/download/v$V/lumen-panel-$V.tar.gz.intoto.jsonl"
gh attestation verify "lumen-panel-$V.tar.gz" --repo luminare-dev/lumen-panel \
  --signer-workflow luminare-dev/lumen-panel/.github/workflows/reusable-release.yml --source-ref refs/heads/main \
  --bundle "lumen-panel-$V.tar.gz.intoto.jsonl"
```

Each command exits with a non-zero status when the check fails; stop then. The `--bundle` form
compares `--repo` only with the repository name recorded in the certificate when the release was
signed: it cannot tell whether the repository has been renamed since or whether another repository
now has that name. The first form fetches the provenance from GitHub and also confirms that it
belongs to the repository that has the name today. The `--bundle` form still downloads Sigstore's
trusted root. On a machine without internet access, run
`gh attestation trusted-root > trusted_root.jsonl` on a connected machine, copy the file over and
add `--custom-trusted-root trusted_root.jsonl`.

## Get the built assets

The themes need the built stylesheets (`lumen.css`, `lumen-dark.css`, `lumen-rtl.css` and
`lumen-dark-rtl.css` for Lumen, `lumen-night.css` and `lumen-night-rtl.css` for Lumen Dark), the
command palette script, the font and the logo files in `/opt/lumen-panel/dist/assets/`; one
folder serves both themes. They are not in git and not in the release archive. Take them from CI,
or build them yourself.

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
with any file neither theme uses.

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
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run                       # Lumen
python3 -m lumen_panel install --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp --dry-run  # Lumen Dark
```

The dry run builds the theme in a temporary folder (removed afterwards), verifies it against the
installed default theme, and checks the owner, write access to `theme/` and the backup folder. It
writes nothing below the panel's web root. A good run prints, among other lines:

```text
dry run: build and verify passed (Lumen, default theme 26.1.1, 7 patches, assets <hash>)
dry run: would build in /home/keyhelp/www/keyhelp/theme/.lumen-staging-<timestamp> and swap it in at /home/keyhelp/www/keyhelp/theme/lumen
dry run: would set owner keyhelp:keyhelp, folders 755, files 644; nothing was written
```

and exits 0. For Lumen Dark the lines read `(Lumen Dark, default theme 26.1.1, 12 patches, ...)`
and name `theme/.lumen-dark-staging-<timestamp>` and `theme/lumen-dark`. Stop on any other result:

- `error: the patch set does not fit this KeyHelp version; nothing was installed`, followed by one
  line per patch that failed (exit 1): this KeyHelp version changed a template at a place the
  patch set relies on. See [After a KeyHelp update](#after-a-keyhelp-update).
- `assets incomplete` or `files the theme does not use` (exit 2): the assets folder is incomplete
  or holds other files; get it again ([Get the built assets](#get-the-built-assets)).

Every exit code is listed in [Configuration](configuration.md#exit-codes).

## Install

```bash
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp                       # Lumen
python3 -m lumen_panel install --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp  # Lumen Dark
```

Install one of them or both; the order does not matter. What `install` does, in this order
(paths for Lumen; Lumen Dark's are in [What the install changes](#what-the-install-changes)):

1. takes the theme's run lock (`/root/backups/lumen-panel/.lock`; a second run for the same theme
   exits 75), creates the backup folder `/root/backups/lumen-panel/<timestamp>/` and moves any
   `theme/.lumen-staging-*` or `theme/.lumen-previous-*` folder an interrupted run left behind
   into its `stale/` folder;
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
install, `Next: KeyHelp -> Configuration -> Appearance -> Theme -> select 'Lumen' and save.` (or
`'Lumen Dark'`).

The install does not select the theme: until you do, the panel keeps showing the theme it showed
before, and the new theme is only listed on the Theme page.

## What the install changes

| Path | Change |
|---|---|
| `/home/keyhelp/www/keyhelp/theme/lumen/` (Lumen), `/home/keyhelp/www/keyhelp/theme/lumen-dark/` (Lumen Dark) | created, or replaced in one atomic rename. Holds `templates/` (the patched copy of the default templates), `assets/` (the theme's own files: Lumen's four stylesheets, or Lumen Dark's two, the command palette, the font and the logo files), `_settings.json` (what the Theme page lists), `_screenshot.png`, the build record `_lumen_build.json` and `LUMEN-README.txt`. Owner `keyhelp:keyhelp`, folders 755, files 644. |
| `theme/.lumen-staging-<timestamp>/`, `theme/.lumen-previous-<timestamp>/` (Lumen), `theme/.lumen-dark-staging-<timestamp>/`, `theme/.lumen-dark-previous-<timestamp>/` (Lumen Dark) | exist only while a run works; a stopped run's folders are moved to the backups by the next run of the same theme. |
| `/home/keyhelp/www/keyhelp/cache/twig/<2 hex>/<hex>.php` | only the compiled templates whose recorded source lies below the theme's own `templates/` folder (`theme/lumen/templates/` or `theme/lumen-dark/templates/`) are moved to the backup folder (`twig-cache/`, and `twig-cache-late/` for the second pass). Every other entry stays, the other theme's included. A first install finds none. |
| `/root/backups/lumen-panel/` | created with mode 700. Lumen's: the run lock `.lock`, the hold file `HOLD` (after a `rollback` or `hold`) and one folder per run, named by its UTC time (for example `20261021T041348050556Z`, so Lumen's run folders are `/root/backups/lumen-panel/2*/`), with `ROLLBACK.txt` and, as the run needs them, `lumen/` (the previous build), `twig-cache/`, `twig-cache-late/`, `stale/` and `failed-staging/`. Lumen Dark keeps the same set in its subfolder `lumen-dark/` (mode 700; its run folders are `/root/backups/lumen-panel/lumen-dark/2*/`), with `lumen-dark/` as the previous build in each run folder. Nothing in it is ever deleted; remove old run folders yourself, and only those that match `2*`: the `lumen-dark/` folder holds Lumen Dark's lock, hold and backups and must stay while Lumen Dark is installed. |
| not changed | the default theme `theme/bulma` (only read), the other lumen-panel theme, KeyHelp's database and settings (the selected theme, the White Label settings), every other file of the panel, the system (no packages; units only if you install them). |

## Check the installed theme

Before you select a theme for all accounts, check the installed folder:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp
ls -ld /home/keyhelp/www/keyhelp/theme/lumen          # owner keyhelp keyhelp
```

For Lumen Dark:

```bash
python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen-dark --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp
python3 -m lumen_panel check-update --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp
ls -ld /home/keyhelp/www/keyhelp/theme/lumen-dark     # owner keyhelp keyhelp
```

`verify` prints one `ok:` line per check (settings, templates, contents, patches, twig syntax,
assets, screenshot; for Lumen Dark also `pro boundary`, which checks that no template can load the
default theme's dark stylesheets and that no patch uses the panel's dark-mode switch or dark
images) and exits 0; `check-update` prints `up to date (Lumen, default theme 26.1.1, lumen-panel
X.Y.Z)` (or `Lumen Dark`) and exits 0. Go on only when both commands exit 0.
`check-update --variant all` checks every installed theme at once.

## Activate Lumen or Lumen Dark in the panel

The selected theme applies to every account on the server, client accounts included, so the steps
below first check, without saving anything, that the panel lists the new theme under its folder
name.

1. Note which theme is active now, as root on the server. Keyweb names the setting
   `default_theme` (table `settings`, category `general`,
   [community forum, Keyweb AG, 2021](https://community.keyhelp.de/viewtopic.php?t=10272)); in
   KeyHelp's database, `SELECT value FROM settings WHERE category = 'general' AND name = 'default_theme';`
   only reads it (`lumen` while Lumen is active, `bulma` for the default theme). That value is
   what you go back to if the new selection fails
   ([If the panel cannot show the Theme page](#if-the-panel-cannot-show-the-theme-page)).
2. Log in to the panel as a main administrator.
3. Open **Configuration**, then **Theme** in the **Appearance** group. The page lists every theme
   folder with its preview, **Description**, **Version**, **Author** and **Website**; its help text
   reads "Change the theme for all accounts on this server."
4. Before the first selection of a theme, view the page source (Ctrl+U) and search for its radio
   button: it must read `name="theme_id" value="lumen-dark"` for Lumen Dark (`value="lumen"` for
   Lumen), the folder name, and the theme's preview image must load on the page. If the value
   differs, do not save; [open an issue](https://github.com/luminare-dev/lumen-panel/issues) with
   what the page shows.
5. Select **Lumen** or **Lumen Dark**.
6. For Lumen, choose the **Default design mode** below it: **Default** (light) or **Dark mode**.
   Every user can still switch with **Enable dark mode** or **Disable dark mode** in the user menu,
   and Lumen follows that switch. Keyweb lists dark mode among the features of KeyHelp Pro on its
   [product page](https://www.keyweb.de/en/keyhelp/keyhelp/); where the panel shows no dark mode,
   Lumen shows its light design. Lumen Dark declares no dark mode, so the page shows no design
   mode for it and the user menu has no switch: it is always dark, for every account.
7. Click **Save**. KeyHelp clears its template cache when the theme changes (changelog of KeyHelp
   19.3, "Template cache now gets deleted when switching between themes").
8. Open the login page in a private browser window and check that it loads the new theme's
   stylesheet (`/theme/lumen-dark/assets/lumen-night.css` for Lumen Dark,
   `/theme/lumen/assets/lumen.css` for Lumen; developer tools, Network tab).

To switch between the two later, select the other one on the same page and save; nothing on disk
changes, and both stay current with `sync`.

The Theme page also notes that White Label settings may need an update to work with the selected
theme. White Label CSS loads after Lumen's stylesheet and wins, so review **Configuration** →
**Appearance** → **White Label** → **Additional CSS** if colours look wrong. A White Label logo for
the internal or external area also wins over the Luminare logo.

## Check it in the browser

Reload once without the cache (Ctrl+Shift+R):

- the login page shows the Luminare logo (or your White Label logo for the external area);
- every page loads `/theme/lumen/assets/lumen.css?v=<hash>`, or its `-dark` or `-rtl` variant
  (developer tools, Network tab), where `<hash>` is the assets hash the install printed; with
  Lumen Dark, `/theme/lumen-dark/assets/lumen-night.css?v=<hash>` (or `lumen-night-rtl.css`)
  after the default theme's `style.css` (or `style-rtl.css`), and never a `style-dark` file;
- Ctrl+K (Cmd+K on a Mac), or the search button in the header, opens the command palette (dark in
  Lumen Dark).

## Switch back, roll back or uninstall

### Switch back at once

**Configuration** → **Appearance** → **Theme** → select **Default Theme** (or the other
lumen-panel theme) → **Save**. Nothing on disk changes, so you can select **Lumen** or **Lumen
Dark** again at any time. `sync` and the optional units keep the installed builds current in the
meantime.

### If the panel cannot show the Theme page

Move the selected theme's folder out of the panel; the command does not ask the panel first:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --yes                       # Lumen
python3 -m lumen_panel uninstall --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp --yes  # Lumen Dark
```

Keyweb's fix for a theme that breaks the panel has two steps: remove the theme's folder, and set
`default_theme` (table `settings`, category `general`) back to `bulma` in KeyHelp's database
([community forum, Keyweb AG, 2021](https://community.keyhelp.de/viewtopic.php?t=10272)). The
command above does the first step without deleting anything. Whether the panel falls back to the
default theme without the second step has not been tested; if pages still fail, do the second
step as Keyweb describes, with the value you noted before the selection (for example `lumen`,
when Lumen Dark failed and Lumen was active before) instead of `bulma`, as long as that theme's
folder is still installed:
`UPDATE settings SET value = 'lumen' WHERE category = 'general' AND name = 'default_theme';`.

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

For Lumen Dark, the backups are in `/root/backups/lumen-panel/lumen-dark/` and every command in
its `ROLLBACK.txt` carries `--variant lumen-dark`:

```bash
cat /root/backups/lumen-panel/lumen-dark/<timestamp>/ROLLBACK.txt
python3 -m lumen_panel rollback --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp --from /root/backups/lumen-panel/lumen-dark/<timestamp>
```

The backup is copied, not moved. A rollback sets a hold on that theme, so `sync` and the units do
not rebuild the version you just left; the next `install` (or `release`) of that theme ends the
hold. A saved theme only goes back as the theme it was built as: a Lumen backup is refused with
`--variant lumen-dark`, and the other way round.

### Uninstall

Each theme is removed on its own; the other one stays installed and selectable.

1. In the panel: **Configuration** → **Appearance** → **Theme**, select **Default Theme** (or the
   other lumen-panel theme, if you keep it) and save.
2. Move the theme folder to the backups:

   ```bash
   cd /opt/lumen-panel/generator
   python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --panel-url https://<your panel>/                       # Lumen
   python3 -m lumen_panel uninstall --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp --panel-url https://<your panel>/  # Lumen Dark
   ```

With `--panel-url`, the command loads the login page once and refuses (exit 4) while it still
loads that theme's stylesheet, and exits 5 when the page cannot be reached or shows neither the
default theme's nor that theme's stylesheet (then re-run with `--yes` after step 1); add
`--insecure` for a self-signed panel certificate. Without it, run the command with `--yes` after
step 1 (it exits 5 otherwise). The removed folder and its compiled templates stay in
`/root/backups/lumen-panel/<timestamp>/` (Lumen) or `/root/backups/lumen-panel/lumen-dark/<timestamp>/`
(Lumen Dark).

To remove everything afterwards: both themes as above, the optional units, if installed
([Rebuild automatically](#rebuild-automatically-optional)), then `/opt/lumen-panel` and, once you
no longer need the backups, `/root/backups/lumen-panel` (Lumen Dark's backups included).

## Rebuild automatically (optional)

lumen-panel ships three example systemd units in `contrib/` and never installs them itself. They
are opt-in:

- `lumen-panel-sync.service` waits 120 seconds (a panel update may still be writing), then runs
  `python3 -m lumen_panel sync --variant all --keyhelp /home/keyhelp/www/keyhelp` once: every
  installed theme, Lumen and Lumen Dark, is rebuilt when it needs it, and a theme that is not
  installed is skipped. It runs with low priority, a 200 MB memory limit and a sandbox (only
  `theme/`, `cache/twig/` and `/root/backups/lumen-panel` are writable, `theme/bulma` stays
  read-only, no network). Exit code 75 starts it again 10 minutes later; it wins over a failure
  of the other theme, so a busy theme is always retried.
- `lumen-panel-sync.path` starts the service when `theme/bulma/_settings.json` changes, which every
  panel update does.
- `lumen-panel-sync.timer` starts the service every day at 05:30 (plus up to 15 minutes of random
  delay) and catches up a run missed while the server was off.

`sync` rebuilds a theme only when the default theme, the generator, that theme's assets or its
patch set changed; otherwise it logs `up to date (...)`. The units assume `/opt/lumen-panel` and
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
python3 -m lumen_panel hold --variant all            # both themes: the units do not rebuild halfway through
cd /opt/lumen-panel
git fetch --tags
git checkout --quiet vX.Y.Z                          # the new release
```

Then replace `dist/assets/` with the assets of the new tag ([Get the built assets](#get-the-built-assets)),
and continue:

```bash
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
cd /opt/lumen-panel/generator
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp     # also ends the hold
# Lumen Dark, if installed:
python3 -m lumen_panel install --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp --dry-run
python3 -m lumen_panel install --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp
```

`install` ends the hold of the theme it installs. A hold set by `hold --variant all` on a theme
that is not installed changes nothing; `python3 -m lumen_panel release --variant all` removes
every hold that is left. If a dry run fails, nothing changed and that theme's hold is still set.
Either fix the cause and run `install`, or go back to the previous tag (`git checkout --quiet vOLD`
and that tag's assets) and run `python3 -m lumen_panel release --variant all`. Do not leave a hold
set: while it is, `sync` does not follow KeyHelp updates for that theme.

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
   python3 -m lumen_panel check-update --variant all --keyhelp /home/keyhelp/www/keyhelp   # 0 current, 10 rebuild needed
   python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
   python3 -m lumen_panel install --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp --dry-run   # if installed
   ```

4. Rebuild (only when needed) and check:

   ```bash
   python3 -m lumen_panel sync --variant all --keyhelp /home/keyhelp/www/keyhelp
   python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
   python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen-dark --keyhelp /home/keyhelp/www/keyhelp   # if installed
   ```

   With the units installed, the `.path` unit starts the same `sync` minutes after the update.

**When a patch anchor no longer fits.** Each patch inserts a few lines next to an anchor that must
occur exactly once in a default template. If the new templates changed at that place, the build
stops with `the patch set does not fit this KeyHelp version; nothing was installed` and names every
failed patch, for example `10-base-stylesheet.json [base-stylesheet]: anchor not found in
layout/base.twig` (Lumen Dark's own patches are named `lumen-dark/<file>`). Nothing is written,
so the previous build of that theme stays active: its templates come
from the older default theme, while the panel's code and the `/theme/bulma/` stylesheets and
scripts are already new. That can break pages. Check the panel, and if a page misbehaves, select
**Default Theme** until the fix is in. Then update lumen-panel (a release for the new KeyHelp
version may exist) or adjust the anchors in `patches/*.json` and `patches/lumen-dark/*.json`, run
the tests and install again
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
**Configuration** → **Appearance** → **Theme**. With a Lumen theme selected, a pasted copy of
Lumen's CSS would load a second time, last, and an older copy would override the newer theme.
Route B covers Lumen only: Lumen Dark needs its template patches (they load the default theme's
standard stylesheet and mark the page with `lumen-night`), which White Label settings cannot
provide.

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
