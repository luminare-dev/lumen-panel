# Upgrading lumen-panel

Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Before 1.0.0 a minor
release may break things; check "BREAKING CHANGES" in the [changelog](../CHANGELOG.md) first.

1. `python3 -m lumen_panel hold --variant all`, so the units do not rebuild halfway through.
2. Check out the new tag (or unpack and [verify](install.md#verify-a-release) the new archive).
3. Replace `dist/assets/` with that tag's assets ([Get the built assets](install.md#get-the-built-assets)).
4. Run `install --dry-run`, then `install`, for each installed theme. `install` ends the hold.
5. [Check the installed theme](install.md#check-the-installed-theme).

If a dry run fails, nothing changed. Fix the cause, or go back to the old tag and run
`python3 -m lumen_panel release --variant all`. Do not leave a hold set.

A KeyHelp update only needs a rebuild, see [docs/update.md](update.md).
