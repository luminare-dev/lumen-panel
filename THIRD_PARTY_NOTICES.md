# Third-party notices

## Included in this repository

| Component | Version | Licence | Where | Source |
|---|---|---|---|---|
| Sora (variable font) | 2.000 | SIL Open Font License 1.1 ([text](assets/fonts/OFL.txt)) | `assets/fonts/Sora[wght].ttf`, unchanged | <https://github.com/sora-xor/sora-font> |

## Bundled into the built files (not in the repository)

`npm run build` writes these into `dist/assets/` (the theme's files) and `gallery/dist/` (the
static gallery). The command palette and every gallery script start with a banner that names
React and React DOM and their licence, and Bulma's stylesheet keeps its own banner;
`scripts/check-island.mjs` and `scripts/check-gallery.mjs` fail the build without them. The
gallery build also copies `LICENSE`, `NOTICE` and this file into `gallery/dist/`.

| Component | Version | Licence | Built file |
|---|---|---|---|
| React, React DOM, scheduler | see `package-lock.json` | MIT, Copyright (c) Meta Platforms, Inc. and affiliates | `dist/assets/lumen-island.js`, `gallery/dist/` |
| Bulma | 0.9.4 | MIT, Copyright (c) 2022 Jeremy Thomas | `gallery/dist/` only (the gallery's base stylesheet) |

Build and test tools (Vite, Rolldown, lightningcss, TypeScript, Vitest, jsdom, Testing Library
and their dependencies) are used to build and test, not distributed; `package-lock.json` lists
them with their licences.

## Not included

No file of KeyHelp (templates, stylesheets, scripts, images, fonts) is part of this repository or
its releases. The generator reads them from the local installation at build time. KeyHelp is a
registered trademark of Keyweb AG.
