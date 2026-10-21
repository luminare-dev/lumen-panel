<!-- header:begin: brand-repos 0.1.0, variant studio, files in docs/brand/; the project-page sync drops this block -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/readme-header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/brand/readme-header-light.svg">
  <img alt="lumen-panel" src="docs/brand/readme-header-light.svg">
</picture>

<!-- byline:studio -->
*a [Luminare Development](https://luminare.tech/open-source/lumen-panel/) open-source project*
<!-- /byline:studio -->
<!-- byline:personal
*by Paul Pasaurek · [project page](https://luminare.tech/open-source/lumen-panel/)*
/byline:personal -->
<!-- header:end -->

# lumen-panel

A modern theme for the KeyHelp hosting panel: a calm, accessible design in light and dark mode, a
React command palette (Ctrl+K) and a generator that builds the theme on the server from the
panel's own default theme. Tested with KeyHelp 26.1.1.

[![ci](https://github.com/luminare-dev/lumen-panel/actions/workflows/ci.yml/badge.svg)](https://github.com/luminare-dev/lumen-panel/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/luminare-dev/lumen-panel?sort=semver)](https://github.com/luminare-dev/lumen-panel/releases)
[![licence](https://img.shields.io/github/license/luminare-dev/lumen-panel)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/luminare-dev/lumen-panel/badge)](https://scorecard.dev/viewer/?uri=github.com/luminare-dev/lumen-panel)

## Screenshot

<!-- Screenshot slot: docs/images/lumen-light.png and docs/images/lumen-dark.png (1280x800),
     taken from the gallery with example data only, shown in a <picture> like the header above. -->
There is no screenshot in the repository yet. The [gallery](#gallery) renders every page and
component in light and dark mode, left to right and right to left.

## Why

The panel's default theme follows Bulma 0.9 defaults; two of its grey text helpers (#7a7a7a at
4.29:1 and #b5b5b5 at 2.05:1 on white) fall below the WCAG AA minimum of 4.5:1, and the panel has
no quick way to jump between its many pages. A theme can fix that, but a theme folder is a full copy of the default templates:
those belong to Keyweb AG, cannot be published, and go stale with every panel update.
lumen-panel publishes only its own work (design tokens, stylesheets, a React command palette, a
React design-system gallery) and a generator that patches a local copy of the default templates
in a few anchored places, verifies the result and swaps it in atomically, with a backup and a
one-command rollback.

## Quickstart

Install on the panel server, as root, with a main administrator account for the panel. The full
guide, with the requirements, the checksum step and what changes on disk, is
[docs/install.md](docs/install.md).

```bash
git clone https://github.com/luminare-dev/lumen-panel.git /opt/lumen-panel   # then check out the newest release tag
# put the CI artifact "theme-assets" (digest checked) into /opt/lumen-panel/dist/assets/
cd /opt/lumen-panel/generator
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp
```

Then, in the panel, select **Lumen** under **Configuration** → **Appearance** → **Theme** and
save. To switch back at once, select **Default Theme** there. Every install saves its undo command
as `ROLLBACK.txt` in its backup folder ([rollback and uninstall](docs/install.md#switch-back-roll-back-or-uninstall)).

After a KeyHelp update, read the [KeyHelp changelog](https://changelog.keyhelp.de/) first, then
rebuild when needed, by hand or with the optional units in `contrib/`
([after a KeyHelp update](docs/install.md#after-a-keyhelp-update)):

```bash
python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp
```

Without a shell, the stylesheet alone also works through the panel's own White Label settings,
without the command palette ([route B](docs/install.md#route-b-white-label-only)).

## How it works

```mermaid
flowchart LR
    src["src/styles<br/>design tokens + components"] -->|"npm run build"| dist[("dist/assets<br/>lumen*.css, island, fonts, logo")]
    island["island/<br/>React command palette (TypeScript)"] -->|"Vite, one IIFE"| dist
    dist -->|"public folder"| gallery[("gallery/dist<br/>static React gallery")]
    bulma[("theme/bulma<br/>installed default theme")] -->|"read-only copy"| gen["generator<br/>python3 -m lumen_panel"]
    patches["patches/*.json<br/>anchored changes"] --> gen
    dist --> gen
    gen -->|"build + verify + atomic swap"| lumen[("theme/lumen")]
    gen -.->|"old build, compiled templates"| backup[("/root/backups/lumen-panel")]
    ci["CI: tests, types, contrast, wording, secret scan"] -.->|"checks every change"| gen
```

### Why no KeyHelp files are in this repository

A KeyHelp theme is a folder with a complete set of Twig templates. The default theme's templates,
stylesheets, scripts and images are Keyweb AG's proprietary files, licensed with each panel; they
may not be published, and a published copy would also be out of date after the next panel
update. So this repository contains none of them, and neither does a release archive or the
`theme-assets` artifact of CI: they hold only lumen-panel's own files. Where a KeyHelp install is
present, a test fails if any file in the repository is a copy of a default theme file. The theme is assembled on the server, from that
panel's own default theme, as a folder of its own below `theme/`, which is how Keyweb describes
own themes ([community forum, Keyweb AG, 2021](https://community.keyhelp.de/viewtopic.php?t=10363)).

### The generator

The generator (`python3 -m lumen_panel`, Python standard library only) assembles the theme on
the server where the panel is installed:

1. It reads `theme/bulma` of the local installation (never changing it) and copies its templates
   byte for byte into a staging folder; if a panel update changes them meanwhile, it stops.
2. It applies the seven patches in `patches/*.json`. Each one inserts a few lines of our own
   markup next to an anchor that must occur exactly once (load the Lumen stylesheet, load the
   palette script on internal pages, show the Luminare logo). If an anchor is missing or
   repeated, nothing is written and every failing patch is listed.
3. It adds Lumen's own files from `dist/assets/`, writes `_settings.json` and a build record
   (default theme version, the hash of every template, the patches, the asset and patch-set
   hashes), and verifies the result: every template must equal the default theme's file, or the
   default theme's file with the patches applied, byte for byte.
4. `install` swaps the staging folder in at `theme/lumen` with one atomic rename; the previous
   build and its compiled Twig templates move to `/root/backups/lumen-panel/<timestamp>/`.
   Nothing is deleted. One run at a time (a lock), and a run that is stopped halfway leaves
   nothing the panel would list as a theme; the next run moves its folders to the backups.

The patched templates keep loading the default theme's own CSS, JavaScript and images from
`/theme/bulma/`, which KeyHelp updates in place. `check-update` and `sync` compare the build
record with the installed default theme, the built assets and the patch set, and rebuild when
one of them changed.

### What you get

- **Stylesheet.** `--lm-*` design tokens from the Luminare brand palette, Sora for type, an 8px
  spacing grid, 10-14px radii, hairline borders instead of heavy shadows, visible focus rings.
  Dark mode follows the panel's own per-user switch; right-to-left pages use the default theme's
  RTL build plus logical properties; reduced motion is respected. Every design-token pair in
  [docs/contrast.md](docs/contrast.md) meets WCAG 2.2 AA in light and dark mode (67 pairs,
  including the default theme's checkboxes, Select2 options, status text on striped and hovered
  rows, close buttons and footnote marks, which Lumen overrides). The table covers the colours
  Lumen sets, not rules of the default theme it leaves alone.
- **Command palette.** Ctrl+K (Cmd+K on a Mac), or the search button in the header, on every
  page after login. It lists the panel's own sidebar and user-menu links, searches them while
  ignoring case and accents, and works fully with the keyboard and a screen reader (modal dialog,
  combobox with a listbox, focus trap, focus returns on close). It renders in shadow roots, so
  its styles and the panel's cannot touch each other, makes no network requests and stores
  nothing ([ADR 0010](docs/adr/0010-the-command-palette-stores-nothing.md)). One deferred script,
  React included, at most 80 KB after gzip (checked by the build; about 72 KB today).
- **Gallery.** A static React app with our own panel-like markup on Bulma 0.9.4: design tokens
  with live contrast numbers, typography, the app shell, cards, tables, pagination, forms,
  buttons, tags, notifications, modals, tabs, the dashboard and the login page, each in light,
  dark, LTR and RTL.

### Gallery

Run it locally (Node.js 22.22.2 or later; no panel needed):

```bash
npm ci --ignore-scripts
npm run dev                         # builds the CSS and the palette, then serves http://localhost:5173/
npm run build && npm run preview    # the static build in gallery/dist/
```

`gallery/dist/` uses relative paths, so it can be served from any folder of any static web
server. The start state can be set in the address, for example `?mode=dark&dir=rtl#forms`. CI
keeps every build of it as the `gallery` artifact for 14 days.

## Design decisions

The decisions behind this project are recorded as short ADRs in [docs/adr/](docs/adr/):

- [ADR 0001: Record architecture decisions](docs/adr/0001-record-architecture-decisions.md)
- [ADR 0002: Pin every action and downloaded tool](docs/adr/0002-pin-actions-and-downloaded-tools.md)
- [ADR 0003: Secret scanning with the gitleaks binary](docs/adr/0003-secret-scanning-with-the-gitleaks-binary.md)
- [ADR 0004: Draft releases with checksums and provenance](docs/adr/0004-draft-releases-with-checksums-and-provenance.md)
- [ADR 0005: Build the theme on the server from the installed default theme](docs/adr/0005-build-the-theme-on-the-server.md)
- [ADR 0006: Small anchored patches that fail loudly](docs/adr/0006-anchored-patches-that-fail-loudly.md)
- [ADR 0007: React for the gallery and one island, not for the panel](docs/adr/0007-react-for-the-gallery-and-one-island.md)
- [ADR 0008: Override by matching selectors, not with cascade layers](docs/adr/0008-override-by-selector-not-by-layer.md)
- [ADR 0009: Atomic swap, backups instead of deletes, narrow cache purge](docs/adr/0009-atomic-swap-backups-and-narrow-cache-purge.md)
- [ADR 0010: The command palette stores nothing, not even a "recent" list](docs/adr/0010-the-command-palette-stores-nothing.md)

**Alternatives.** The panel's White Label settings (Configuration → Appearance → White Label)
take logos, a favicon, additional CSS and JavaScript; that is the right tool for a logo and a few
colours, the lighter [route B](docs/install.md#route-b-white-label-only) uses it for Lumen's
stylesheet alone, and the theme keeps White Label CSS and logos working on top. A hand-maintained
copy of the default theme gives full control over the markup, but it cannot be shared and drifts
with every panel update.

## Supported versions

| Component | Tested with | Supported |
|---|---|---|
| KeyHelp (default theme `bulma`) | 26.1.1 on Ubuntu 24.04 (generator build, verify and dry run on the live install, read-only) | 26.1.x; other versions when every patch anchor still fits (the dry run and every build check it) |
| Operating system | Ubuntu 24.04 | the systems KeyHelp runs on (Keyweb lists Ubuntu LTS and Debian) |
| Python (generator) | 3.12 | 3.10 or later |
| Node.js (only to build the assets) | 22.x in CI (GitHub's ubuntu-24.04 runner) | 22.22.2 or later (22.x), 24.15 or later, 26 |
| Browsers | not yet tested in a browser | written for Chrome/Edge 111+, Firefox 121+, Safari 16.4+ |

How compatibility is checked:

- **Every build**, the dry run included, needs each patch anchor exactly once in the installed
  default templates; otherwise nothing is written and every failing patch is listed.
- **Every build is verified** byte for byte against the installed default theme (each template is
  equal, or equal with the patches applied), and the patched templates pass a Twig syntax check.
- **`check-update`** compares the default theme's version and a hash over all its templates with
  the build record, so a KeyHelp update, or a KeyHelp patch that only changes templates, is
  noticed (exit 10).
- **The tests** check every anchor against the local KeyHelp install when one is present; CI builds
  and verifies a theme on every commit against a fake panel tree of our own.
- **Before a KeyHelp update**, read the [KeyHelp changelog](https://changelog.keyhelp.de/) for
  changes to the template system, themes or White Label
  ([after a KeyHelp update](docs/install.md#after-a-keyhelp-update)).

Fixes go into the latest minor release only. See the
[security policy](https://github.com/luminare-dev/.github/blob/main/SECURITY.md) for reporting.

## Limitations

- Only the default theme's markup is restyled; pages a panel update adds look right only as far
  as they use the same Bulma components.
- After a panel update, `sync` must run (manually or from the units) before the copied templates
  match the panel again; until then, the previous build stays active. When a patch no longer fits,
  that previous build keeps running against the new panel until the patch set is fixed
  ([runbook](docs/runbook.md#failure-lumen-panel-syncservice-failed)).
- The Luminare logo replaces the KeyHelp logo on every panel page, also for client accounts.
- Releases carry the source archive only. The built assets come from the CI artifact
  `theme-assets`, which GitHub keeps for 30 days, or from a build with Node.js on another machine.
- With the White Label route alone there is no command palette, no Sora font and only part of the
  login page design ([route B](docs/install.md#route-b-white-label-only)).
- The command palette knows only the links of the sidebar and the user menu, not the actions
  inside pages, and it has no "recent pages" list.
- Sora covers Latin only: in the Russian, Arabic and Chinese panels the whole page uses the
  system font instead.
- Chart.js charts and the code and text editors (CodeMirror, Trumbowyg) keep the default theme's
  colours ([docs/keyhelp-markup.md](docs/keyhelp-markup.md)).

## Results

| What | Value | How it was measured |
|---|---|---|
| Contrast, text pairs | 51 pairs, lowest 4.55:1 (light) and 4.51:1 (dark), minimum 4.5:1 | `python3 scripts/contrast.py`, WCAG 2.x formula, 2026-10-21; full table in [docs/contrast.md](docs/contrast.md) |
| Contrast, UI parts | 16 pairs (control borders, focus rings, progress fills, close-button crosses), lowest 3.17:1 (light) and 3.08:1 (dark), minimum 3:1 | same |
| Generator and repository tests | 172 Python tests pass, 4 skipped (gitleaks and markdownlint-cli2 not installed, one template-only test) | `LUMEN_BRAND_KIT=<kit> python3 -m unittest discover -s tests`, 2026-10-21, with the KeyHelp 26.1.1 install present (read-only) |
| Generator against the live panel | build and verify pass: 215 templates, 211 byte for byte equal to the default theme, 4 patched files reproduce exactly; dry run passes | `python3 -m lumen_panel build` and `verify --keyhelp` into a scratch folder with placeholder assets, KeyHelp 26.1.1, read-only, 2026-10-21 |
| Command palette tests | 41 tests pass (Vitest, jsdom, Testing Library) | `npm test` in CI (Node.js 22), 2026-10-21 |
| Command palette size | 71.8 KB after gzip (CI, 2026-10-21); the build fails above 80 KB | `node scripts/check-island.mjs` |
| Stylesheet size | about 46 KB per variant, minified (four variants) | `node scripts/build-css.mjs` in CI, 2026-10-21 |

## Documentation and links

- [Installation](docs/install.md) (the theme, or the White Label route) ·
  [Keeping it current after KeyHelp updates](docs/update.md) ·
  [Configuration](docs/configuration.md) · [Upgrading lumen-panel](docs/upgrade.md) ·
  [Troubleshooting](docs/troubleshooting.md) · [Runbook](docs/runbook.md) · [ADRs](docs/adr/) ·
  [Panel markup inventory](docs/keyhelp-markup.md) · [Contrast table](docs/contrast.md) ·
  [Official KeyHelp resources](docs/keyhelp-resources.md)
- [Changelog](CHANGELOG.md) (written by release-please) and
  [releases](https://github.com/luminare-dev/lumen-panel/releases) (each release has
  `SHA256SUMS`, and a build provenance attestation while the repository is public)
- [Contributing](https://github.com/luminare-dev/.github/blob/main/CONTRIBUTING.md) ·
  [Code of conduct](https://github.com/luminare-dev/.github/blob/main/CODE_OF_CONDUCT.md) ·
  [Security](https://github.com/luminare-dev/.github/blob/main/SECURITY.md) ·
  [Support](https://github.com/luminare-dev/.github/blob/main/SUPPORT.md)
- Project page: <https://luminare.tech/open-source/lumen-panel/>

## Official KeyHelp resources

KeyHelp is developed by Keyweb AG; for the panel itself, these official pages are the reference
(each checked on 2026-10-21; what each one says is recorded in
[docs/keyhelp-resources.md](docs/keyhelp-resources.md)):

- [KeyHelp product page](https://www.keyweb.de/en/keyhelp/keyhelp/) (`www.keyhelp.de` redirects
  there)
- [Overview of all functions](https://www.keyweb.de/en/keyhelp/keyhelp/overview-of-all-functions):
  "With the white-label function, you can tailor the server hosting tool to your design ideas:
  Use your own logo and adapt styles and functions to your own wishes and needs. In addition, you
  can also develop your own themes."
- [Install KeyHelp](https://www.keyweb.de/en/keyhelp/keyhelp/#install): requirements and the
  installer of the panel itself
- [Knowledge base](https://kb.keyhelp.de/) with the user and administrator manual
  ([English](https://kb.keyhelp.de/index.php?ln=en))
- [Tutorials](https://www.keyweb.de/en/support/learn-more/tutorials#keyhelp), among them
  "Install KeyHelp" and "Customize with white label"
- [Changelog](https://changelog.keyhelp.de/): read it before every KeyHelp update
- [Community forum](https://community.keyhelp.de/), "The official KeyHelp forum of Keyweb AG",
  for example Keyweb's notes on [own themes and the KeyHelp logo](https://community.keyhelp.de/viewtopic.php?t=10363)
- [REST API documentation](https://api.keyhelp.de) (opens on SwaggerHub; lumen-panel does not use
  the API)

## Not affiliated

KeyHelp is a registered trademark of Keyweb AG. lumen-panel is not affiliated with or endorsed by
Keyweb AG. "KeyHelp" is named only to describe what this project works with. This repository
contains no KeyHelp file. lumen-panel never uses or changes the KeyHelp logo files, and its
documentation does not link them: the theme shows its own logo in their place, or your White
Label logo. The theme is built from the
KeyHelp installation on the server where it runs
([why](#why-no-keyhelp-files-are-in-this-repository)).

## Licence

[MIT](LICENSE). The licence covers the code only: the project name, logo, header images,
`docs/brand/` and `assets/brand/` are not licensed (see [NOTICE](NOTICE)). The Sora font keeps its
own licence ([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

<!-- byline:studio -->
*a [Luminare Development](https://luminare.tech/open-source/lumen-panel/) open-source project*
<!-- /byline:studio -->
<!-- byline:personal
*by Paul Pasaurek · [project page](https://luminare.tech/open-source/lumen-panel/)*
/byline:personal -->
