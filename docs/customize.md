# Customizing

Lumen and Lumen Dark read a Lumen token file: colours for light and dark mode, fonts, text size,
corner radius, spacing, shadows, logos, favicon, login background and custom CSS. The same token
files work in the other Lumen themes (the Pterodactyl and Hydrodactyl themes and the browser
themes), so one file gives every tool the same look.

## The customizer

`lumen-panel-customizer.html` is one HTML file that runs offline: open it in a browser, no server
needed. Its Content-Security-Policy blocks every network request, and nothing you load leaves the
page. Get it from the `customizer` artifact of a CI run (or a release), or build it yourself after
`npm run build:css`:

```bash
node customizer/build.mjs --assets dist/assets --bulma node_modules/bulma/css/bulma.min.css \
  --out dist/customizer/lumen-panel-customizer.html
```

What it edits:

- **Preset:** Luminare (default), Graphite (neutral, KeyHelp's own logo), Aurora, High contrast.
- **Colours:** the 16 colour roles of each mode, with a picker and a hex field. Pairs below
  WCAG 2.2 AA (4.5:1 for text, 3:1 for the focus ring) are marked and listed with their ratio.
- **Typography:** heading, body and code fonts, text size (85 to 125 %), heading weight.
- **Shape, spacing and layout:** corner radius, spacing unit, density, shadow strength, card
  borders, the style of the active menu item, the glow on the login page.
- **Branding:** product name (used as logo text and alt text), a logo for light mode and one for
  dark mode and Lumen Dark, favicon, login background. PNG, JPEG, WebP, GIF, ICO or SVG up to
  4 MB; the files go into the ZIP. A font file (WOFF2 or WOFF) for custom CSS.
- **Custom CSS:** added after the tokens. Use the variables (`var(--lm-surface)`,
  `var(--lumen-accent)`) so your rules follow both modes. Uploaded files are
  `url("/storage/lumen/<file>")`.

The preview is a mock of the panel (our own markup with the panel's class names, styled by the
real Lumen stylesheets) in light mode, in the panel's dark mode and as Lumen Dark, with the
dashboard and the login page. **Export tokens** saves the token file; **Download customization
ZIP** saves everything the server needs. **Import** takes a token file from any Lumen theme or a
ZIP made here (then the uploads come back too).

Token values that only other Lumen themes use are kept in the file but change nothing here:
KeyHelp keeps its own sidebar and content layout (`layout.sidebar`, `sidebarWidth`,
`contentWidth`) and its per-user dark-mode switch (`mode.*`); the theme cannot load a font
stylesheet from another server (`typography.stylesheet`).

## Install a customization

On the panel server, in the generator folder of your lumen-panel checkout:

```bash
cd /opt/lumen-panel/generator
python3 -m lumen_panel apply-custom /root/lumen-panel-example.zip --keyhelp /home/keyhelp/www/keyhelp
python3 -m lumen_panel apply-custom /root/lumen-panel-example.zip --keyhelp /home/keyhelp/www/keyhelp --yes
```

The first command is a dry run: it checks the ZIP and builds and verifies every installed variant
with it in a temporary folder, and writes nothing. With `--yes` it

1. moves the current customization (`custom/` in the checkout) to
   `/root/backups/lumen-panel/custom/<timestamp>/`,
2. writes the new one to `custom/`,
3. installs each installed variant the usual way (backup of `theme/<variant>`, atomic swap,
   Twig cache), and
4. puts the previous customization back if an install fails.

It prints the undo command at the end: `apply-custom <backup folder> --yes`, or
`apply-custom --reset --yes` when there was no customization before. `--reset` removes the
customization and rebuilds with the plain Lumen look. `--variant lumen` or `--variant lumen-dark`
limits it to one theme.

Every later `install` and `sync` (also after a KeyHelp update) uses `custom/`, and
`check-update` reports a changed customization as a reason to rebuild. `--custom DIR` points any
command at another folder.

### What the ZIP holds and what is checked

| File | Content |
|---|---|
| `lumen.tokens.json` | the token file |
| `override-follow.css` | appended to `lumen.css` and `lumen-rtl.css` (light, dark under the panel's dark mode) |
| `override-dark.css` | appended to Lumen's dark stylesheets and to Lumen Dark's |
| `branding.json` | logos for the header and login page, favicon, product name |
| `custom/<file>` | your uploads, copied to `theme/<variant>/assets/custom/` |

No KeyHelp file is in the ZIP. The generator refuses any other file, file types that are not
images or fonts, content that does not match the type, SVG files with scripts, event handlers,
`<use>`, animations, entities or outside references, CSS that is not a compiled override, and
branding values that are not a shipped logo, an uploaded file, an https URL or empty.

An empty logo brings back KeyHelp's logo in Lumen and shows the product name in Lumen Dark (Lumen
Dark never uses the dark-mode images of the panel). A white-label logo set in KeyHelp still wins
over the theme's logo; a customization's favicon wins over the white-label favicon.

## Compile a token file without the customizer

`tokens/compile.mjs` writes the same folder from a token file (Node.js 22.6 or newer, no
packages). Put uploaded files into its `custom/` subfolder yourself:

```bash
node --experimental-strip-types tokens/compile.mjs my.lumen.json --out custom/
node --experimental-strip-types tokens/compile.mjs --preset aurora --out custom/
```

## How the tokens reach the theme

`tokens/core.ts` and the presets are copies of the Lumen token compiler of
[lumen-hydrodactyl-theme](https://github.com/luminare-dev/lumen-hydrodactyl-theme)
(`shared.lock` names the commit; `scripts/check_shared.py` checks the copies, and with `fetch` the
source too). The schema is described in that repository's `docs/tokens.md`.

`tokens/keyhelp.ts` turns the compiled `--lumen-*` variables into the theme's own: every
component of Lumen reads the role variables of `src/styles/tokens.css` (`--lm-surface`,
`--lm-primary`, `--lm-text-muted` ...), and the override sets each of them from the 16 colour
roles, for example `--lm-primary-tint: color-mix(in srgb, var(--lumen-accent) 10%,
var(--lumen-surface))`. Radii and spacing follow the token radius and spacing unit, fonts and
heading weight the typography. CI checks that the customizer page embeds exactly this compiler
(`tests/parity/run.mjs`) and builds both themes with every preset.
