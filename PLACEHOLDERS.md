# Placeholders

This repository was created from
[luminare-dev/oss-template](https://github.com/luminare-dev/oss-template). Every placeholder of the
template is filled; CI fails if one comes back. The values used:

| Placeholder | Value |
|---|---|
| `{{SLUG}}` | `lumen-panel` (project page `https://luminare.tech/open-source/lumen-panel/`) |
| `{{PROJECT_TITLE}}` | `lumen-panel` |
| `{{ONE_LINE_PURPOSE}}` | A modern theme for the KeyHelp hosting panel (README, first paragraph) |
| `{{PROBLEM_STATEMENT}}` | README, section "Why" |
| `{{QUICKSTART_COMMANDS}}` | README, section "Quickstart", and `docs/install.md` |
| `{{TARGET_SYSTEM}}` | the README diagram shows the theme folders of the panel install |
| `{{COMPONENT}}`, `{{TESTED_VERSION}}`, `{{SUPPORTED_RANGE}}` | README, "Supported versions"; `docs/install.md`, "Requirements" |
| `{{LIMITATION}}` | README, "Limitations" |
| `{{RESULT}}`, `{{VALUE}}`, `{{METHOD}}` | README, "Results" |
| `{{SPDX_ID}}` | `MIT` |
| `{{AUTHOR_NAME}}` | `Paul Pasaurek` (LICENSE, NOTICE, the inactive personal byline) |
| `{{YEAR}}` | `2026` |
| `{{VERSION}}` | no release with manual upgrade steps yet; `docs/upgrade.md` has no version notes |

## Values to check, not placeholders

| Value | Where | Status |
|---|---|---|
| `ci / lint-test`, `assets`, `secrets / gitleaks`, `pr / pr-title`, `DCO` | repository ruleset (required checks) | set when the repository is created (PUBLISHING.md, A7) |
| `luminare-dev` | README badges and links | the organization |
| `docs/brand/` | header SVGs and social preview | generated for `lumen-panel` by brand-repos (studio variant) |
| `release-please-config.json` -> `initial-version` | first release | `0.1.0` |
| `version.txt`, `package.json`, `generator/lumen_panel/__init__.py` | release-please | start at `0.0.0`; release-please updates all three |
