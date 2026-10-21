# Panel markup inventory

What the Lumen stylesheet and the patch set rely on, written down from a read-only look at the
default theme of KeyHelp 26.1.1 (`theme/bulma`, 215 template files) on 2026-10-21. This page
describes the markup in our own words; it does not reproduce the templates.

## Rendering and stylesheets

- The panel renders server-side with Twig 3 (3.11.3 bundled) and enhances pages with jQuery,
  Chart.js, tippy.js (tooltips) and Select2 4.1 (search fields).
- The default theme's stylesheet is compiled from Bulma 0.9.4 with panel-specific additions. It
  uses no CSS custom properties. There are four builds: `style.css`, `style-dark.css`,
  `style-rtl.css` and `style-dark-rtl.css`.
- `layout/base.twig` picks the build from two switches: the user's dark mode
  (`_app.theme.is_dark_mode`) and the text direction (`_app.text_direction`). Then come the
  page's own CSS block and, last, the white-label CSS from the panel settings.
- `<body>` carries `dark-mode` or `default-mode`; `<html>` carries `lang` and `dir`. A
  `color-scheme` meta tag follows the mode.
- Dark mode is a per-user toggle in the user menu (it reloads the page); a theme declares
  support with `has_dark_mode` in `_settings.json`. Keyweb lists dark mode among the features of
  KeyHelp Pro. Lumen declares it and follows the toggle; Lumen Dark declares no dark mode, pins the
  standard stylesheet (`style.css` or `style-rtl.css`), sets the colour scheme to dark (and the
  `theme-color` of the default favicon tags to the Night background) and adds a `lumen-night` class to `<html>` and `<body>` next to the panel's own body class
  ([ADR 0011](adr/0011-lumen-dark-is-a-design-not-the-pro-dark-mode.md)).
- All script and image paths in the templates point at `/theme/bulma/` (or `theme/bulma/`), so a
  copied template set keeps using the default theme's current assets.
- Content Security Policy of the panel: `default-src 'self' 'unsafe-inline' 'unsafe-eval'`,
  `img-src * data:`, `font-src *`. Lumen loads only same-origin files.

## Layouts

| Layout | Used for | Logo |
|---|---|---|
| `layout/intern.twig` | every page after login | header `#header > #top-nav`, inside the home link |
| `layout/extern.twig` | login and password reset | at the top of the login `.box` |
| `layout/popup.twig` | small popup windows (service details, whois) | header, like the internal layout |

In all three, the logo is either the white-label logo (when one is configured under the panel's
white-label settings) or the default theme's logo file. The patch set replaces only the second
branch, so a configured white-label logo still wins. The default theme's logo files are never
read, changed or copied.

## App shell (internal layout)

| Part | Selector | Notes |
|---|---|---|
| Header | `#header` (fixed, 4rem high), `#top-nav .level` | area name and clock in `.has-text-grey`; icon tiles built from a stacked square and a white glyph (`.fa-stack`, `.fa-square`, `.fa-inverse`) |
| User menu | `#user-menu` (fixed, slides under the header) | `a.dropdown-item` entries: profile, dark mode switch, logout; `.dropdown-divider` |
| Sidebar | `#sidebar` (fixed, 250px), `#sidebar-navigation.menu` | groups `.app-menu-group` with a clickable `.menu-label` (collapses the group) and `.menu-list > li > a`; the current page has `a.is-active`; each item starts with a small chevron in `<small>` |
| Overlay | `#sidebar-overlay` | below 1024px when the sidebar is open |
| Content | `#content-wrapper > #content` | breadcrumbs `.breadcrumb.is-small`, page title `.content-title h1.title.is-4`, events, page content |
| Footer | `#footer .content` | white-label footer or the default copyright lines |

## Components

| Component | Classes | Notes |
|---|---|---|
| Card | `.card`, `.card-header` (`.is-collapsible`), `.card-header-icon` (often first), `.card-header-title`, `.card-content`, `.card-footer`, `.card-footer-item` | every page section; `.has-equal-height`, `.is-card-on-card` |
| Box | `.box` | the login form |
| Table | `.table-container > .table.is-fullwidth.is-striped.is-hoverable` | `.has-valigned-cells`, `th` in `tbody` for key/value tables, `.is-narrow` columns |
| Form field | `.field`, `.label`, `.control`, `.input`, `.textarea`, `.select > select`, `.checkbox`, `.radio`, `.help` | grey help text above the field, `.has-addons` for addons and the show-password button, `.button.is-static` units, `.file.is-link.has-name` uploads |
| Button | `.button` plus a style: primary `.is-link`, secondary `.is-danger`, grey `.is-dark` | `.is-outlined` tooltip buttons, `.is-loading` while a form submits, `.buttons` groups |
| Tag | `.tag` with `.is-info`, `.is-danger` and others | the edition tag and the "outdated" tag |
| Message | `article.message.is-{info,success,warning,danger} > .message-body` | the panel's events; `.has-delete` with a `.delete` link |
| Notification | `.notification` | rare |
| Modal | `.modal > .modal-background + .modal-card` (`-head`, `-title`, `-body`, `-foot`) | connection data, DKIM; above tooltips |
| Tabs | `.tabs.is-centered.is-boxed > ul > li.is-active > a`, panels `.tabs-panel.is-active` | |
| Pagination | `.pagination.is-centered`, `.pagination-previous/-next` (with a `disabled` attribute), `.pagination-link.is-current`, `.pagination-ellipsis` | |
| Usage meter | `.usage-indicator` with `progress.progress[data-load-level]` (low, medium, high) | CPU load text `.cpu-load[data-load-level] .cpu-load-percent` |
| Tooltip | tippy.js with the `light-border` theme | `.tippy-box[data-theme~=light-border]`, arrows per placement |
| Search field | Select2 4.1, default theme | `.select2-container--default`, `.select2-selection--single/--multiple`, `.select2-dropdown`, `.select2-results__option--highlighted/--selected` |
| Lists | `ul.horizontal-separated-list` | items separated by "/" |
| Helpers | `.has-text-grey`, `.has-text-grey-light`, `.has-text-link`, `.has-text-danger`, ... | Bulma helpers with `!important`; Bulma's greys are below 4.5:1 on white |

## Theme folder

- A theme is a folder below `theme/` with `_settings.json` (`name`, `description`, `author`,
  `version`, `website`, `path_to_templates`, `has_dark_mode`), `_screenshot.png` (500x250 in the
  default theme) and the templates. The admin selects it under Configuration → Appearance → Theme.
- Custom theme folders survive panel updates, but their copied templates do not change with the
  default theme. That is why the generator records the default theme's version and a hash of
  its templates, and `check-update` compares them.

## Twig cache

`cache/twig/<2 hex>/<hex>.php`, one compiled class per template. Each file ends with
`getSourceContext()`, which records the template's logical name and its absolute path, for
example `.../theme/bulma/templates/layout/base.twig`. Templates of another theme folder have
other paths and therefore other cache files. The generator uses only that recorded path to find
the compiled Lumen templates (see `generator/lumen_panel/twigcache.py`).

## What CSS cannot restyle

- **Charts.** The dashboards draw with Chart.js on `<canvas>`; the colours (blue, green, red
  series, segment borders) are set in the panel's JavaScript and chosen by its dark-mode switch,
  so a stylesheet cannot change them. In Lumen they keep the default theme's colours. In Lumen
  Dark the panel draws them for a light page: the doughnut charts (no text, an HTML legend in the
  panel's colours next to them) stay as drawn; the monitoring charts (`canvas.app-chart` with
  `data-chart-datasets`, the only ones with axis labels and a legend) are shown inverted with the
  hue turned back by a CSS filter, so their grey labels become `#999999` (6.20:1 on the card).
- **Editors.** CodeMirror (file manager, template editors) uses its own theme, and Trumbowyg
  (rich text) its own neutral greys; the panel picks CodeMirror's theme and wraps Trumbowyg with
  its dark-mode switch. In Lumen both stay as the default theme sets them, also in dark mode. In
  Lumen Dark, where the panel picks their light look, `night/editors.css` restyles both with the
  dark tokens; their stylesheets load after Lumen's, so those rules carry the `lumen-night` class.
- **Images for light backgrounds.** The vendor logo on the admin dashboard (`.svg-vendor-logo`)
  and the KeyDisc mark on the backup pages (`.svg-keydisc`) are chosen by the dark-mode switch.
  Lumen Dark leaves the files alone and shows them on a small light plate.
- **Embedded pages.** The Rspamd web interface is an `<iframe>` whose theme the panel sets from
  its dark-mode switch; it stays light in Lumen Dark.
- **Rules with `!important`.** Where the default theme marks a colour `!important` (Select2's
  selected option and shown value, `pre` backgrounds), Lumen either overrides it with
  `!important` of its own (Select2, see `select2.css`) or works with it (`pre` stays transparent
  and gets a border).
