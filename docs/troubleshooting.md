# Troubleshooting

## "the patch set does not fit this KeyHelp version; nothing was installed"

**Cause:** a KeyHelp update changed a template, so a patch anchor occurs zero times or more than
once. The message names each failing patch, for example
`10-base-stylesheet.json [base-stylesheet]: anchor not found in layout/base.twig`.

**Fix:** nothing was changed on the panel. Update the anchor in the named patch file to the new
template text (it must occur exactly once; Lumen Dark's own patches are in `patches/lumen-dark/`),
run `python3 -m unittest discover -s tests`, which also checks every anchor of both themes against
the local install, and install again.

## "assets incomplete: ... missing (run 'npm run build')"

**Cause:** `dist/assets/` does not exist or is from an older build.

**Fix:** put the CI artifact `theme-assets` of the commit you checked out into `dist/assets/`
(digest checked), or build the assets on another machine and copy them; building on the server
only with the memory-limited commands ([Get the built assets](install.md#get-the-built-assets)).
Do not run `npm` there without a limit: on a small server it can push other programs out of
memory.

## "files the theme does not use: ..."

**Cause:** `dist/assets/` holds a file the theme does not load (an old bundle, a source map).
Everything below `theme/lumen/assets/` and `theme/lumen-dark/assets/` would be downloadable from
the panel, so the build only takes the themes' stylesheets (`lumen*.css`), `lumen-island.js`,
`fonts/*`, `brand/*.svg` and the files the patches list.

**Fix:** delete the named files, or rebuild: `npm run build:css` empties `dist/assets/` first.

## "another lumen-panel run is active" or "the default theme changed during the build" (exit 75)

**Cause:** a second run, or a KeyHelp update that was still writing the default theme.

**Fix:** nothing was installed; run the command again a few minutes later. See the
[runbook](runbook.md#exit-code-75-busy-or-the-default-theme-changed-during-the-build).

## Lumen or Lumen Dark is not listed under Configuration → Appearance → Theme

**Cause:** `theme/lumen/_settings.json` (or `theme/lumen-dark/_settings.json`) is missing or not
readable by the panel user, or that theme was never installed (`install --variant lumen-dark`
installs Lumen Dark; a plain `install` installs Lumen only).

**Fix:** check the folder and its owner, then verify it:

```bash
ls -l /home/keyhelp/www/keyhelp/theme/lumen/_settings.json /home/keyhelp/www/keyhelp/theme/lumen-dark/_settings.json
cd /opt/lumen-panel/generator
sudo python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
sudo python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen-dark --keyhelp /home/keyhelp/www/keyhelp
```

## Lumen Dark has no dark-mode switch and no "Default design mode"

**Cause:** none; this is how it is meant to be. Lumen Dark is always dark by its own stylesheet and
declares no dark mode, so the panel shows neither the switch in the user menu nor the design mode
on the Theme page for it. It does not use the dark mode of KeyHelp Pro
([ADR 0011](adr/0011-lumen-dark-is-a-design-not-the-pro-dark-mode.md)).

**Fix:** for a light panel, select **Lumen** (or the default theme) instead.

## Parts of a page stay light in Lumen Dark

**Cause:** a part that no stylesheet can reach: the panel's images made for light backgrounds
(shown on a small light plate on purpose), the doughnut charts on the dashboards, or the embedded
Rspamd interface. Or White Label CSS that sets light colours (it loads after Lumen Dark on
purpose), or a browser cache with an older stylesheet.

**Fix:** reload without the cache (Ctrl+Shift+R) and review **Additional CSS** on the White Label
page. Anything else that stays light is a missing rule: open an issue with the page and the
element (the developer tools show its classes).

## The theme is selected but pages still look like the default theme

**Cause:** the browser still has the old stylesheet, or White Label CSS overrides the colours
(it loads after Lumen on purpose).

**Fix:** reload without the cache (Ctrl+Shift+R). Every build changes the `?v=` value of the Lumen
files, so a normal reload is enough after the next build. Review **Additional CSS** under
**Configuration** → **Appearance** → **White Label** (the **All languages** entry and every
language entry).

## Ctrl+K does not open the command palette

**Cause:** the palette loads only on pages after login, and it leaves Ctrl+K to code and text
editors (file manager, template editors). Some browser extensions take Ctrl+K first.

**Fix:** click into the page outside an editor and press Ctrl+K again (Cmd+K on a Mac). Check that
`/theme/lumen/assets/lumen-island.js` (Lumen Dark: `/theme/lumen-dark/assets/lumen-island.js`)
loads (browser developer tools, Network tab).

## The asset build stops with an out-of-memory error

**Cause:** too little free memory for the build on a small server.

**Fix:** use the CI artifact `theme-assets`, or build on another machine and copy `dist/assets/`
to the server, or run the build with a memory limit when enough memory is free
([Get the built assets](install.md#get-the-built-assets)).

## The panel shows errors after selecting Lumen or Lumen Dark, and the Theme page does not load

**Cause:** a template of the build fails with this panel version.

**Fix:** move the selected theme's folder out of the panel (the command does not ask the panel
first):

```bash
cd /opt/lumen-panel/generator
sudo python3 -m lumen_panel uninstall --keyhelp /home/keyhelp/www/keyhelp --yes                       # Lumen
sudo python3 -m lumen_panel uninstall --variant lumen-dark --keyhelp /home/keyhelp/www/keyhelp --yes  # Lumen Dark
```

Keyweb's fix for a theme that breaks the panel has two steps: remove the theme's folder, and
set `default_theme` (table `settings`, category `general`) back to `bulma` in KeyHelp's database
([community forum, Keyweb AG, 2021](https://community.keyhelp.de/viewtopic.php?t=10272)). The
command above does the first step without deleting anything. Whether the panel falls back to the
default theme without the second step has not been tested; if pages still fail, do the second
step as Keyweb describes
([If the panel cannot show the Theme page](install.md#if-the-panel-cannot-show-the-theme-page)).
Then open an issue with the KeyHelp version and the template the error names.

When the Theme page still loads, select **Default Theme** there first (nothing on disk changes),
then [roll back](install.md#roll-back-to-the-previous-build) to the previous build if there is
one.

## Still stuck?

Search the [issues](https://github.com/luminare-dev/lumen-panel/issues), then open one. Never post
secrets, keys, IP addresses, hostnames or customer data; redact logs before you paste them.
