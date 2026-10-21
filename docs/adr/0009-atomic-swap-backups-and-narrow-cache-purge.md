# 0009. Atomic swap, backups instead of deletes, narrow cache purge

- **Status:** accepted
- **Date:** 2026-10-21

## Context

The theme is installed on a live panel used by several accounts. A half-written theme folder or
a stale compiled template must never be served, and an install must be easy to undo.

## Considered options

1. Write into `theme/lumen` in place and clear the whole Twig cache.
2. Build next to the target, verify, swap with renames, back up the old folder and move only the
   compiled templates that belong to Lumen.

## Decision

Chosen option 2. The build goes to `theme/.lumen-staging-<timestamp>`, is verified and then
swapped in with `renameat2(RENAME_EXCHANGE)` where available (two renames otherwise). The old
folder and the compiled Lumen templates go to `/root/backups/lumen-panel/<timestamp>/`; nothing
is deleted. A compiled template is attributed to Lumen only when the source path it records lies
below `theme/lumen/templates/`. Each run writes `ROLLBACK.txt`.

## Consequences

- Good: the panel sees either the old or the new theme; every step can be undone.
- Good: the default theme and its compiled templates are never touched.
- Bad: backups accumulate and are cleaned up by the admin.
