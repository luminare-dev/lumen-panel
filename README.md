<!-- header:begin: brand-repos 0.1.0, variant studio, files in docs/brand/; the project-page sync drops this block -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/readme-header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/brand/readme-header-light.svg">
  <img alt="lumen-panel" src="docs/brand/readme-header-light.svg">
</picture>

<!-- byline:studio -->
*a [Luminare Development](https://luminare.tech/open-source/) open-source project*
<!-- /byline:studio -->
<!-- byline:personal
*by Paul Pasaurek · [project page](https://luminare.tech/open-source/lumen-panel/)*
/byline:personal -->
<!-- header:end -->

# lumen-panel

Two themes for the KeyHelp hosting panel, **Lumen** (light, follows the panel's dark mode) and
**Lumen Dark** (always dark), with a Ctrl+K command palette. A small generator builds them on the
server from the panel's own default theme. Tested with KeyHelp 26.1.1.

[![ci](https://github.com/luminare-dev/lumen-panel/actions/workflows/ci.yml/badge.svg)](https://github.com/luminare-dev/lumen-panel/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/luminare-dev/lumen-panel?sort=semver)](https://github.com/luminare-dev/lumen-panel/releases)
[![licence](https://img.shields.io/github/license/luminare-dev/lumen-panel)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/luminare-dev/lumen-panel/badge)](https://scorecard.dev/viewer/?uri=github.com/luminare-dev/lumen-panel)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/15777/badge)](https://www.bestpractices.dev/projects/15777)

| Lumen | Lumen Dark |
|---|---|
| ![Lumen: a light panel with white cards](assets/brand/theme-screenshot.png) | ![Lumen Dark: a dark panel](assets/brand/theme-screenshot-dark.png) |

![Dashboard in the Lumen theme](docs/screenshots/lumen-dashboard.png)

Lumen Dark is its own stylesheet on top of the panel's light stylesheet. It is not the dark mode
of KeyHelp Pro and does not enable or use it.

KeyHelp's default templates belong to Keyweb AG and are not in this repository. The generator
copies them from the local install, applies a few anchored patches, verifies the result and swaps
the theme in atomically, with a backup and a rollback command.

## Install

On the panel server, as root (full guide: [docs/install.md](docs/install.md)):

```bash
git clone https://github.com/luminare-dev/lumen-panel.git /opt/lumen-panel   # then check out the newest release tag
# put the CI artifact "theme-assets" (digest checked) into /opt/lumen-panel/dist/assets/
cd /opt/lumen-panel/generator
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp --dry-run
python3 -m lumen_panel install --keyhelp /home/keyhelp/www/keyhelp
python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
```

Then select **Lumen** under **Configuration** → **Appearance** → **Theme**. For Lumen Dark, add
`--variant lumen-dark` to each command. After a KeyHelp update, rebuild with
`python3 -m lumen_panel sync --variant all --keyhelp /home/keyhelp/www/keyhelp`, or install the
optional systemd units in `contrib/` ([docs/update.md](docs/update.md)).

## Development

```bash
npm ci --ignore-scripts
npm run dev                          # builds the assets and serves the gallery on http://localhost:5173/
python3 -m unittest discover -s tests
```

## Documentation and links

[Install](docs/install.md) · [After a KeyHelp update](docs/update.md) ·
[Upgrading](docs/upgrade.md) · [Configuration](docs/configuration.md) ·
[Troubleshooting](docs/troubleshooting.md) · [Runbook](docs/runbook.md) ·
[Contrast table](docs/contrast.md) · [Changelog](CHANGELOG.md)

[Contributing](https://github.com/luminare-dev/.github/blob/main/CONTRIBUTING.md) ·
[Code of conduct](https://github.com/luminare-dev/.github/blob/main/CODE_OF_CONDUCT.md) ·
[Security](https://github.com/luminare-dev/.github/blob/main/SECURITY.md) ·
[Support](https://github.com/luminare-dev/.github/blob/main/SUPPORT.md)

KeyHelp is a registered trademark of Keyweb AG. lumen-panel is not affiliated with or endorsed by
Keyweb AG.

## Licence

[MIT](LICENSE). The project name, logo and the files in `docs/brand/` and `assets/brand/` are not
licensed (see [NOTICE](NOTICE)). The Sora font has its own licence
([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

<!-- byline:studio -->
*a [Luminare Development](https://luminare.tech/open-source/) open-source project*
<!-- /byline:studio -->
<!-- byline:personal
*by Paul Pasaurek · [project page](https://luminare.tech/open-source/lumen-panel/)*
/byline:personal -->
