# Installation

There are two ways to use lumen-panel:

- **Route A, the themes** (most of this guide): Lumen and/or Lumen Dark as theme folders, with the
  command palette and the login page design. Needs a root shell on the panel server.
- **[Route B, White Label only](#route-b-white-label-only)**: paste Lumen's stylesheet into the
  panel's White Label settings. Needs only a browser; no command palette, no Lumen Dark.

| | Lumen | Lumen Dark |
|---|---|---|
| Folder | `theme/lumen` | `theme/lumen-dark` |
| Option | `--variant lumen` (default) | `--variant lumen-dark` |
| Look | light; dark when the panel's dark mode (KeyHelp Pro) is on | always dark |
| Backups | `/root/backups/lumen-panel/<timestamp>/` | `/root/backups/lumen-panel/lumen-dark/<timestamp>/` |

The two themes never share a folder, lock or backup, so you can install either or both. The
commands below are for Lumen; add `--variant lumen-dark` for Lumen Dark.

## Requirements

- KeyHelp 26.1.x (26.1.1 tested) with the default theme `bulma` present and unmodified. Other
  versions work as long as every patch anchor still fits, which the [dry run](#dry-run) checks.
- Ubuntu or Debian, as supported by KeyHelp (Ubuntu 24.04 tested).
- A main administrator account in the panel and a root shell on the server.
- Python 3.10 or later (standard library only) and git.
- Node.js only if you build the assets yourself (22.22.2+, 24.15+ or 26), preferably on another
  machine.

The paths assume a standard KeyHelp install (`/home/keyhelp/www/keyhelp`) and the checkout in
`/opt/lumen-panel`, where the units in `contrib/` expect it. Run every command as root.

## Get the code

```bash
git clone https://github.com/luminare-dev/lumen-panel.git /opt/lumen-panel
cd /opt/lumen-panel
git tag --list 'v*' --sort=-v:refname | head -n 1     # the newest release
git checkout --quiet vX.Y.Z
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
```

The generator runs as root, so nobody else may be able to write to the checkout.

### Alternative: the release archive

```bash
V=X.Y.Z
cd /root
curl -fsSLO "https://github.com/luminare-dev/lumen-panel/releases/download/v$V/lumen-panel-$V.tar.gz"
curl -fsSLO "https://github.com/luminare-dev/lumen-panel/releases/download/v$V/SHA256SUMS"
sha256sum -c SHA256SUMS
tar -xzf "lumen-panel-$V.tar.gz" -C /opt && mv "/opt/lumen-panel-$V" /opt/lumen-panel
chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel
```

### Verify a release

Releases carry signed SLSA build provenance. Check it with the [GitHub CLI](https://cli.github.com/):

```bash
gh attestation verify "lumen-panel-$V.tar.gz" --repo luminare-dev/lumen-panel \
  --signer-workflow luminare-dev/lumen-panel/.github/workflows/reusable-release.yml --source-ref refs/heads/main
```

Without a GitHub login, download `lumen-panel-$V.tar.gz.intoto.jsonl` from the release and add
`--bundle "lumen-panel-$V.tar.gz.intoto.jsonl"`. Stop if any check fails.

## Get the built assets

The themes need the built stylesheets, the palette script, the font and the logos in
`/opt/lumen-panel/dist/assets/`. They are not in git or the release archive.

### From CI

CI keeps the built assets of every commit as the artifact `theme-assets` for 30 days. Download
the one for the commit you checked out and compare its SHA-256 digest:

```bash
COMMIT=$(git -C /opt/lumen-panel rev-parse HEAD)
RUN=$(gh run list --repo luminare-dev/lumen-panel --workflow ci.yml --commit "$COMMIT" --status success \
  --json databaseId --jq '.[0].databaseId')
gh api "repos/luminare-dev/lumen-panel/actions/runs/$RUN/artifacts" \
  --jq '.artifacts[] | select(.name == "theme-assets") | "\(.id) \(.digest)"'
gh api "repos/luminare-dev/lumen-panel/actions/artifacts/<artifact id>/zip" > theme-assets.zip
echo "<digest without sha256:>  theme-assets.zip" | sha256sum -c -
```

Unpack it on the server:

```bash
cd /opt/lumen-panel
rm -rf dist/assets && mkdir -p dist/assets
python3 -m zipfile -e /root/theme-assets.zip dist/assets/
head -c 30 dist/assets/lumen.css; echo                  # must show the generator's version
(cd generator && python3 -m lumen_panel version)
chown -R root:root dist && chmod -R go-w dist
```

### Build them yourself

On a machine with Node.js, from the same tag:

```bash
npm ci --ignore-scripts
npm run build:css && npm run build:island
tar -C dist -cf - assets | ssh root@<panel host> \
  'rm -rf /opt/lumen-panel/dist/assets && mkdir -p /opt/lumen-panel/dist && tar -C /opt/lumen-panel/dist -xf -'
```

Avoid building on a small panel server: an unbounded `npm` run can push mail or ClamAV out of
memory. If you must, wrap each command in
`systemd-run --scope -p MemoryMax=450M env NODE_OPTIONS=--max-old-space-size=320 ...`.

## Dry run

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
```

This builds and verifies the theme in a temporary folder and writes nothing below the panel's web
root. It should end with `dry run: ... nothing was written` and exit 0. If it reports
`the patch set does not fit this KeyHelp version`, see [After a KeyHelp update](#after-a-keyhelp-update);
`assets incomplete` means `dist/assets/` needs to be fetched again. Exit codes are listed in
[Configuration](configuration.md#exit-codes).

## Install

```bash
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp
```

`install` builds the theme in a staging folder next to `theme/lumen`, verifies it, sets the owner
to `keyhelp:keyhelp` and swaps it in with one rename. The previous build and its compiled Twig
templates move to the backup folder, together with a `ROLLBACK.txt`. Nothing is deleted. The
install does not select the theme.

## Check the installed theme

```bash
python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp
```

Both must exit 0 (`verify` prints only `ok:` lines).

## Activate Lumen or Lumen Dark in the panel

1. Log in as a main administrator and open **Configuration** → **Appearance** → **Theme**.
2. Select **Lumen** or **Lumen Dark**. For Lumen, pick the **Default design mode** too.
3. Click **Save**, then open the login page in a private window and check that it loads
   `/theme/lumen/assets/lumen.css` (or `/theme/lumen-dark/assets/lumen-night.css`).

The theme applies to all accounts. White Label CSS and logos still load on top of it. Ctrl+K (or
the search button in the header) opens the command palette.

## Switch back, roll back or uninstall

To switch back at once, select **Default Theme** on the Theme page and save. Nothing on disk
changes.

### If the panel cannot show the Theme page

Move the theme folder out of the panel:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --yes
```

If pages still fail, set the theme back in KeyHelp's database as Keyweb describes
([forum](https://community.keyhelp.de/viewtopic.php?t=10272)):
`UPDATE settings SET value = 'bulma' WHERE category = 'general' AND name = 'default_theme';`

### Roll back to the previous build

```bash
cat /root/backups/lumen-panel/<timestamp>/ROLLBACK.txt
python3 -m lumen_panel rollback --keyhelp /home/keyhelp/www/keyhelp --from /root/backups/lumen-panel/<timestamp>
```

A rollback sets a hold, so `sync` does not rebuild the version you left. The next `install` (or
`release`) ends it.

### Uninstall

Select **Default Theme** in the panel first, then:

```bash
python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --panel-url https://<your panel>/
```

With `--panel-url` the command refuses while the login page still loads the theme; without it,
pass `--yes`. The removed folder stays in the backups. To remove everything, also remove the
units from `contrib/` if installed, `/opt/lumen-panel` and `/root/backups/lumen-panel`.

## Rebuild automatically (optional)

`contrib/` has a systemd service, a path unit (runs after each panel update) and a daily timer
that run `sync --variant all`. See [docs/update.md](update.md#rebuild-automatically-optional-units).

## Update lumen-panel

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel hold --variant all
cd /opt/lumen-panel && git fetch --tags && git checkout --quiet vX.Y.Z
```

Replace `dist/assets/` with the new tag's assets, then run the [dry run](#dry-run) and
[install](#install) again for each installed theme (`install` ends the hold). If you give up
instead, run `python3 -m lumen_panel release --variant all` so `sync` follows KeyHelp updates
again. See also [Upgrading lumen-panel](upgrade.md).

## After a KeyHelp update

A KeyHelp update replaces `theme/bulma` but keeps `theme/lumen`, whose templates are then older
than the panel. Read the [KeyHelp changelog](https://changelog.keyhelp.de/) first, then:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel check-update --variant all --keyhelp /home/keyhelp/www/keyhelp   # 10 = rebuild needed
python3 -m lumen_panel sync --variant all --keyhelp /home/keyhelp/www/keyhelp
```

If a patch anchor no longer fits, nothing is written and the previous build stays active. Check
the panel, select **Default Theme** if pages break, and update lumen-panel or the anchors in
`patches/` ([details](update.md#when-the-patch-set-does-not-fit-the-new-templates)).

## Route B: White Label only

1. Get `lumen-rtl.css` from the `theme-assets` artifact or a build (about 46 KB).
2. In the panel, open **Configuration** → **Appearance** → **White Label** and edit
   **All languages**.
3. Paste the file into **Additional CSS**, check **Preview on this page**, and save.
4. Optionally upload your own logos. Do not upload a changed KeyHelp logo.

Keep **Default Theme** selected while you use route B. You get Lumen's colours and layout in light
and dark mode, but not the Sora font, the command palette, the full login page or Lumen Dark. To
undo, empty **Additional CSS** and save. Route B has not been tried on a live panel yet.
