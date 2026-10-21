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

Amended 2026-10-21 after a production-safety review: runs take an exclusive lock on the backup
root; the backup folder is created before anything is written; folders an interrupted run left in
`theme/` are moved to the backups by the next run; any exception or `SIGTERM` before the swap
moves the staging folder out; right after the swap the replaced tree's `_settings.json` is
renamed (so the panel never lists it), the compiled Lumen templates are moved, `ROLLBACK.txt` is
written, and only then is the old tree moved to the backups, with a second cache pass two seconds
later. A rollback sets a hold that stops `sync` until the next `install`.

## Consequences

- Good: the panel sees either the old or the new theme; every step can be undone.
- Good: the default theme and its compiled templates are never touched.
- Bad: backups accumulate and are cleaned up by the admin.
