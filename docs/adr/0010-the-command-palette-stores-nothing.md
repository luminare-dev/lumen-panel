# 0010. The command palette stores nothing, not even a "recent" list

- **Status:** accepted
- **Date:** 2026-10-21

## Context

Command palettes often show the last pages a user opened. In the panel that list would have to
live in the browser: `localStorage` (kept for good) or `sessionStorage` (kept until the tab
closes). The panel's links carry more than page names: their query strings can hold ids of
accounts, domains and mailboxes, and both storages can be read by every script on the panel's
origin, including scripts a panel update adds later. Several people can use the same browser
profile at a provider's desk, and client accounts sign in to the same origin as the administrator.

## Considered options

1. A "recent" list of full links in `localStorage`.
2. A "recent" list of up to five links in `sessionStorage`, cleared when the tab closes.
3. No list: the palette rebuilds its entries from the page's own navigation each time it opens.

## Decision

Chosen option 3. With an empty query the palette shows the panel's own menu in menu order, with
the current page marked, so the first keystrokes already reach every page; a "recent" list would
save little. The palette reads the DOM, keeps its state in memory only, and makes no network
request. The unit tests check that it never calls `fetch`, `XMLHttpRequest` or `Storage`, and
`scripts/check-island.mjs` fails the build if the bundled file mentions a network or storage API.

## Consequences

- Good: the privacy statement is short and checkable: the palette sees only what the page shows
  and forgets it when the page unloads. Nothing to clear on logout, nothing shared between
  accounts.
- Good: entries always match the signed-in user's permissions, because they come from the menu
  the panel rendered for that user.
- Bad: frequently used pages deep in a long menu need a few letters every time.
- Revisit if users ask for it: option 2 would store only paths without query strings.
