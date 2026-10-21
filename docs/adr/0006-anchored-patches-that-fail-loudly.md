# 0006. Small anchored patches that fail loudly

- **Status:** accepted
- **Date:** 2026-10-21

## Context

The theme needs a few template changes: load the Lumen stylesheet and the command palette, show
the Luminare logo, mark the login hero. Panel updates may change any template.

## Considered options

1. Unified diffs applied with fuzz.
2. Regular expressions.
3. Exact anchor strings that must occur exactly once, with insert-before, insert-after or
   replace, kept in one JSON file per patch.

## Decision

Chosen option 3. Every patch names its file, an anchor and the text; each inserted text starts
with a marker comment (`{# lumen-panel:<id> #}`). All patches are applied in memory first. If one
anchor occurs zero or several times, nothing is written and every failing patch is listed. Verify
then checks that each marker occurs exactly once and that the patched templates still have
balanced Twig blocks.

## Consequences

- Good: a template change can never be patched in the wrong place; the panel keeps the previous
  build until the patch set is fixed.
- Good: anchors are short template lines used only to locate a change.
- Bad: any change at an anchor needs a manual update of that patch, even when it is harmless.
