# 0007. React for the gallery and one island, not for the panel

- **Status:** accepted
- **Date:** 2026-10-21

## Context

The owner asked for a modern React design. The panel renders every page on the server with Twig
and enhances it with jQuery; replacing that would mean rewriting a proprietary application.

## Considered options

1. Rewrite pages as a React application against the panel's API.
2. Restyle the server-rendered markup with CSS only.
3. Restyle with CSS, and use React where it fits: a design-system gallery for development and a
   small client-side island inside the panel.

## Decision

Chosen option 3. The visual design is one stylesheet over the panel's markup. React renders the
gallery (our own panel-like markup, built with Vite) and the command palette (Ctrl+K, and a small
search button in the header), which is one deferred IIFE file written in TypeScript. The palette
renders into shadow roots, reads the panel's own navigation from the page, makes no network
request and stores nothing ([ADR 0010](0010-the-command-palette-stores-nothing.md)).

## Consequences

- Good: panel behaviour, permissions and forms stay KeyHelp's; the palette cannot break the
  panel's styles and the panel's styles cannot break it.
- Good: the gallery shows every component in light, dark, LTR and RTL without a panel.
- Bad: the palette script bundles React and React DOM, which make up most of the file (the
  build fails above 80 KB after gzip, `scripts/check-island.mjs`; React 19 + React DOM are about 60 KB of it); browsers load it once per
  build thanks to the `?v=` cache key.
