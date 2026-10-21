# 0011. Lumen Dark is a design of its own, not the dark mode of KeyHelp Pro

- **Status:** accepted
- **Date:** 2026-10-21

## Context

A second theme was requested that is always dark, also on panels without a KeyHelp Pro licence.
The panel's own dark mode belongs to KeyHelp Pro (Keyweb lists it among the features of KeyHelp
Pro on its [product page](https://www.keyweb.de/en/keyhelp/keyhelp/)): the switch in the user
menu, the "Default design mode" option on the Theme page, the dark stylesheets of the default
theme (`style-dark.css`, `style-dark-rtl.css`) and its `dark/` image variants. The `has_dark_mode`
flag in `_settings.json` only says that a theme follows that switch. The default theme declares it
on every edition, including panels without Pro (`theme/bulma/_settings.json` of KeyHelp 26.1.1),
so a theme that declares it, as Lumen does to match the default theme, gets exactly what the
default theme gets. A theme could still hand out that part of KeyHelp Pro by forcing the
template variable `_app.theme.is_dark_mode`, or by loading the dark stylesheets or `dark/` images
from `/theme/bulma/` regardless of it. A theme must not do that.

## Considered options

1. Force the dark mode on (the template variable `_app.theme.is_dark_mode`, or the default design
   mode) in a theme that declares `has_dark_mode`.
2. Load the default theme's dark stylesheet from Lumen Dark's templates.
3. Draw the dark design entirely with lumen-panel's own stylesheet, on top of the default theme's
   standard (light) stylesheet, the way any custom theme may restyle the panel; declare no dark
   mode, and check that it stays that way.

## Decision

Chosen option 3. Lumen Dark (`theme/lumen-dark`) loads `style.css` or `style-rtl.css` of the
default theme whatever the panel's dark-mode setting says (a template patch pins the standard
stylesheet), then its own `lumen-night.css` (the Lumen components with the dark token set, plus
`src/styles/night.css` for everything the light base still paints light). Its `_settings.json`
says `has_dark_mode: false`, so the panel offers no switch for it, and its description says that
it is not the dark mode of KeyHelp Pro: it does not enable or unlock it, has no dark-mode switch,
and loads none of its dark stylesheets or images. The template patches add a `lumen-night` class
to `<html>` and `<body>` and leave the panel's own body class alone; they never set or read the
dark-mode switch, and the logos are lumen-panel's own files.

Checks keep the boundary: `verify` fails a Lumen Dark build in which a template can load a dark
stylesheet of the default theme or a patch text uses the dark-mode switch, the dark stylesheets
or `dark/` images; the tests and CI check the same in the patch set, the templates and the built
stylesheets.

## Consequences

- Good: Lumen Dark adds nothing that loads, sets or reads the panel's dark mode. Its patches never
  use the switch, the dark stylesheets or the `dark/` images, and the panel's own unchanged
  templates pick `dark/` images only when the panel itself reports dark mode, which it does not
  offer without KeyHelp Pro or for a theme that declares none.
- Good: the Pro boundary is checked on every build, not only reviewed once.
- Bad: every light surface of the standard stylesheet needs a dark rule of our own; a live test
  re-runs the audit against the installed stylesheet, so a panel update that adds one is noticed.
- Bad: what a stylesheet cannot reach stays as the panel draws it for light pages: the panel's
  images for light backgrounds (shown on a small light plate), the doughnut charts (white segment
  borders included), and the embedded Rspamd interface. The monitoring charts are shown inverted
  by a CSS filter. The rich text editor's editing area stays a light sheet, because the colours
  its toolbar offers are inline styles made for white.
- Bad: inside Lumen Dark there is no per-user light mode; an administrator switches the theme for
  all accounts (Lumen and Lumen Dark can both be installed).
