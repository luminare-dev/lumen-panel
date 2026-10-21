# Troubleshooting

## "the patch set does not fit this KeyHelp version; nothing was installed"

**Cause:** a KeyHelp update changed a template, so a patch anchor occurs zero times or more than
once. The message names each failing patch, for example
`10-base-stylesheet.json [base-stylesheet]: anchor not found in layout/base.twig`.

**Fix:** nothing was changed on the panel. Update the anchor in the named patch file to the new
template text (it must occur exactly once), run `python3 -m unittest discover -s tests`, which
also checks every anchor against the local install, and install again.

## "assets incomplete: ... missing (run 'npm run build')"

**Cause:** `dist/assets/` does not exist or is from an older build.

**Fix:**

```bash
npm ci --ignore-scripts && npm run build
```

On a server with little free memory, run the build with a limit, for example
`systemd-run --scope -p MemoryMax=450M -p MemorySwapMax=0 npm run build`, or build on another
machine and copy `dist/assets/` over.

## Lumen is not listed under Configuration -> Theme

**Cause:** `theme/lumen/_settings.json` is missing or not readable by the panel user.

**Fix:** check the folder and its owner, then verify it:

```bash
ls -l /home/keyhelp/www/keyhelp/theme/lumen/_settings.json
cd generator && sudo python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen --keyhelp /home/keyhelp/www/keyhelp
```

## The theme is selected but pages still look like the default theme

**Cause:** the browser still has the old stylesheet, or a white-label CSS overrides the colours
(it loads after Lumen on purpose).

**Fix:** reload without the cache (Ctrl+Shift+R). Every build changes the `?v=` value of the Lumen
files, so a normal reload is enough after the next build. Review the white-label CSS in the panel
settings.

## Ctrl+K does not open the command palette

**Cause:** the palette loads only on pages after login, and it leaves Ctrl+K to code and text
editors (file manager, template editors). Some browser extensions take Ctrl+K first.

**Fix:** click into the page outside an editor and press Ctrl+K again (Cmd+K on a Mac). Check that
`/theme/lumen/assets/lumen-island.js` loads (browser developer tools, Network tab).

## The asset build stops with an out-of-memory error

**Cause:** too little free memory for the build on a small server.

**Fix:** build on another machine and copy `dist/assets/` to the server, or run the build with a
memory limit when enough memory is free (see [Installation](install.md)).

## Still stuck?

Search the issues, then ask in the organization's
[Discussions](https://github.com/orgs/luminare-dev/discussions). Never post secrets, keys, IP
addresses, hostnames or customer data; redact logs before you paste them.
