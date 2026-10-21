# Third-party notices

## Included in this repository

| Component | Version | Licence | Where | Source |
|---|---|---|---|---|
| Sora (variable font) | 2.000 | SIL Open Font License 1.1 ([text](assets/fonts/OFL.txt)) | `assets/fonts/Sora[wght].ttf`, unchanged | <https://github.com/sora-xor/sora-font> |

## Bundled into the built files (not in the repository)

`npm run build` writes these into `dist/`; their licence notices travel with the built files.

| Component | Version | Licence | Built file |
|---|---|---|---|
| React, React DOM, scheduler | see `package-lock.json` | MIT, Copyright (c) Meta Platforms, Inc. and affiliates | `dist/assets/lumen-island.js`, `dist/gallery/` |
| Bulma | 0.9.4 | MIT, Copyright (c) 2023 Jeremy Thomas | `dist/gallery/` only (the gallery's base stylesheet) |

Build tools (Vite, Rolldown, lightningcss and their dependencies) are used to build, not
distributed; `package-lock.json` lists them with their licences.

## Not included

No file of KeyHelp (templates, stylesheets, scripts, images, fonts) is part of this repository or
its releases. The generator reads them from the local installation at build time. KeyHelp is a
registered trademark of Keyweb AG.
