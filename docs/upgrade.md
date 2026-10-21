# Upgrading lumen-panel

Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Before 1.0.0 a minor
release may contain breaking changes; they are listed under "BREAKING CHANGES" in the
[changelog](../CHANGELOG.md), which release-please writes from the Conventional Commit titles.

A KeyHelp update is a different case: it needs a rebuild of the theme, not a new lumen-panel. See
[Keeping the theme current after a KeyHelp update](update.md).

## Steps

The exact commands are in [Installation, Update lumen-panel](install.md#update-lumen-panel).

1. Read the changelog entries between your version and the new one.
2. With the optional units installed, run `python3 -m lumen_panel hold` (and
   `python3 -m lumen_panel hold --variant lumen-dark` when Lumen Dark is installed), so they do
   not rebuild while the code and the assets do not match yet.
3. Fetch the new release: `git fetch --tags` and `git checkout --quiet vX.Y.Z` (or unpack the new
   release archive after `sha256sum -c SHA256SUMS`).
4. Replace `dist/assets/` with the assets of the new tag: the CI artifact `theme-assets` of that
   commit with its digest checked, or a build on another machine
   ([Get the built assets](install.md#get-the-built-assets)); afterwards
   `chown -R root:root /opt/lumen-panel && chmod -R go-w /opt/lumen-panel` again.
5. Run `install --dry-run`, then `install` for each installed theme (add `--variant lumen-dark`
   for Lumen Dark; see [Installation](install.md#install)). The previous build is kept in the
   backups, and `install` ends that theme's hold from step 2. If a dry run fails, nothing changed
   and the hold is still set: fix the cause and run `install`, or go back to the previous tag and
   its assets and run `python3 -m lumen_panel release` (with the same `--variant`). Do not leave a
   hold set, because `sync` does not follow KeyHelp updates for that theme while it is.
6. Run the check from [Installation](install.md#check-the-installed-theme) again.

If the optional units are installed and no hold is set, the daily timer picks up the new
generator version, the new assets and a changed patch set by itself: each counts as "rebuild
needed". Steps 2 and 5 are still the safer way, because a dry run shows problems before anything
changes.
