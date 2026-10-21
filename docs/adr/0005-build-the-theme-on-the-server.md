# 0005. Build the theme on the server from the installed default theme

- **Status:** accepted
- **Date:** 2026-10-21

## Context

A KeyHelp theme is a folder with a full set of Twig templates. The default theme's templates,
stylesheets, scripts and images belong to Keyweb AG and are licensed with each KeyHelp install;
they must not be published. Custom theme folders also go stale: a panel update changes the
default templates but not the copies.

## Considered options

1. Publish a complete theme folder (copies of the default templates with our changes).
2. Write every template from scratch.
3. Publish only our own files and a generator that copies the templates from the local install,
   applies a small patch set and adds our assets.

## Decision

Chosen option 3. The repository holds the generator, the patch set, the stylesheets, the command
palette and the gallery, and nothing of KeyHelp. The theme is assembled where KeyHelp is
licensed, and rebuilt by `sync` after each panel update. Templates keep loading the default
theme's assets from `/theme/bulma/`, so those stay current without being copied.

## Consequences

- Good: no proprietary file in the repository or its releases; the theme follows panel updates
  with one command.
- Good: the visual work lives in one stylesheet over the default markup, so it survives template
  changes that do not touch the patched lines.
- Bad: the server needs Python and the built assets; a template change at a patch anchor needs a
  patch update (ADR 0006 keeps that failure loud and harmless).
