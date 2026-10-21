# Upgrading

Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Before 1.0.0 a minor
release may contain breaking changes; they are listed under "BREAKING CHANGES" in the
[changelog](../CHANGELOG.md).

## After a KeyHelp update

A panel update replaces the default theme but leaves `theme/lumen` alone, so the copied templates
can be older than the panel. Check and rebuild:

```bash
cd generator
sudo python3 -m lumen_panel check-update --keyhelp /home/keyhelp/www/keyhelp   # 10 = rebuild needed
sudo python3 -m lumen_panel sync --keyhelp /home/keyhelp/www/keyhelp           # rebuild only when needed
```

`check-update` reports a rebuild when the default theme's version, its templates (sha256) or the
generator version differ from the build record. `sync` runs `install` in that case; the previous
build goes to the backups as usual. A timer can run `sync` daily (see the [runbook](runbook.md)).

If `sync` stops with "the patch set does not fit this KeyHelp version", the panel keeps running
on the previous Lumen build, whose templates come from the older default theme. Until the patch
set is updated, select the default theme if a page misbehaves. Then update the anchors in
`patches/*.json` to the new templates (each anchor must occur exactly once), run the tests and
install again.

## Upgrading lumen-panel

1. Read the changelog entries between your version and the new one.
2. Fetch the new release (or `git pull`), then `npm ci && npm run build`.
3. Run `install --dry-run`, then `install` (see [Installation](install.md)). The previous build
   is kept in the backups.
4. Run the check from [Installation](install.md) again.
