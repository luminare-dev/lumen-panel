# Upgrading lumen-panel

Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Before 1.0.0 a minor
release may contain breaking changes; they are listed under "BREAKING CHANGES" in the
[changelog](../CHANGELOG.md), which release-please writes from the Conventional Commit titles.

A KeyHelp update is a different case: it needs a rebuild of the theme, not a new lumen-panel. See
[Keeping the theme current after a KeyHelp update](update.md).

## Steps

1. Read the changelog entries between your version and the new one.
2. Fetch the new release (or `git pull`), then rebuild the assets, on another machine or with
   the memory-limited commands in [Installation](install.md#install); afterwards
   `chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel` again.
3. Run `install --dry-run`, then `install` (see [Installation](install.md)). The previous build
   is kept in the backups.
4. Run the check from [Installation](install.md#check-that-it-works) again.

If the optional units are installed, the daily timer picks up the new generator version, the new
assets and a changed patch set by itself: each counts as "rebuild needed" (not while a hold is
set). Step 3 is still the safer way, because a dry run shows problems before anything changes.
