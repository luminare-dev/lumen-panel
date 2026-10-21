# 0008. Override by matching selectors, not with cascade layers

- **Status:** accepted
- **Date:** 2026-10-21

## Context

The default theme's stylesheet is compiled Bulma 0.9.4 without custom properties and without
cascade layers. Lumen loads right after it and before the page CSS and the white-label CSS.

## Considered options

1. Put the Lumen rules in `@layer`.
2. Raise specificity everywhere (ids, `!important`).
3. Repeat the selector Bulma uses for each state and win by source order; use `!important` only
   where Bulma does (colour helpers).

## Decision

Chosen option 3. Unlayered rules beat layered ones, so option 1 would lose to the default theme.
Option 2 would also beat the white-label CSS, which must keep the last word. Colours, spacing and
radii come from `--lm-*` design tokens; spacing and borders use logical properties, so the default
theme's RTL builds keep working. A test rejects `@layer` and physical margins or offsets other than
resets.

## Consequences

- Good: white-label CSS and page CSS can still override Lumen.
- Good: dark mode is a token swap under `body.dark-mode`.
- Bad: every Bulma state selector has to be mirrored; the button file is long.
