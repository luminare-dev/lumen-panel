// Build the four stylesheets the patched base template loads, plus the fonts and logo files:
//
//   dist/assets/lumen.css           light (dark mode applies under body.dark-mode)
//   dist/assets/lumen-dark.css      + dark tokens on :root
//   dist/assets/lumen-rtl.css       + right-to-left additions
//   dist/assets/lumen-dark-rtl.css  + both
//   dist/assets/fonts/              Sora variable font and its OFL
//   dist/assets/brand/              Luminare logo files (not licensed, see NOTICE)
//
// The dark :root block is not written by hand: it is the dark-mode block of tokens.css, so the
// two can never drift apart. Run: node scripts/build-css.mjs

import { bundle, transform } from "lightningcss";
import { cpSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "dist", "assets");
const styles = join(root, "src", "styles");
const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));

// Browsers the stylesheet is written for (logical properties, :has(), inset): lightningcss
// encodes versions as major << 16 | minor << 8.
const targets = { chrome: 111 << 16, edge: 111 << 16, firefox: 121 << 16, safari: (16 << 16) | (4 << 8) };

const DARK_SELECTOR = ":root:has(> body.dark-mode),\nbody.dark-mode {";

function darkRootBlock() {
  const css = readFileSync(join(styles, "tokens.css"), "utf8");
  const start = css.indexOf(DARK_SELECTOR);
  if (start < 0) throw new Error("tokens.css: dark-mode block not found");
  const bodyStart = start + DARK_SELECTOR.length;
  const end = css.indexOf("}", bodyStart);
  return `\n/* -dark build: dark tokens on :root too */\n:root {${css.slice(bodyStart, end)}}\n`;
}

function bundled(file) {
  const { code } = bundle({ filename: join(styles, file), targets, minify: false, errorRecovery: false });
  return code.toString();
}

function minified(name, css) {
  const { code, warnings } = transform({ filename: name, code: Buffer.from(css), targets, minify: true });
  for (const w of warnings) console.warn(`${name}: ${w.message}`);
  return code.toString();
}

const banner =
  `/*! lumen-panel ${pkg.version} | MIT | a Luminare Development open-source project | ` +
  "https://github.com/luminare-dev/lumen-panel | Not affiliated with or endorsed by Keyweb AG. " +
  "KeyHelp is a registered trademark of Keyweb AG. */\n";

const base = bundled("index.css");
const rtl = bundled("rtl.css");
const dark = darkRootBlock();
const variants = {
  "lumen.css": base,
  "lumen-dark.css": base + dark,
  "lumen-rtl.css": base + rtl,
  "lumen-dark-rtl.css": base + dark + rtl,
};

// Start from an empty folder: every file in dist/assets ends up below the panel's public web root,
// so nothing old (a previous bundle, a source map) may stay behind. build:island runs after this.
rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
for (const [name, css] of Object.entries(variants)) {
  const code = banner + minified(name, css) + "\n";
  writeFileSync(join(out, name), code);
  console.log(`dist/assets/${name}  ${code.length} bytes`);
}

cpSync(join(root, "assets", "fonts"), join(out, "fonts"), { recursive: true });
mkdirSync(join(out, "brand"), { recursive: true });
for (const file of readdirSync(join(root, "assets", "brand"))) {
  if (file.endsWith(".svg")) cpSync(join(root, "assets", "brand", file), join(out, "brand", file));
}
console.log("dist/assets/fonts and dist/assets/brand copied");
