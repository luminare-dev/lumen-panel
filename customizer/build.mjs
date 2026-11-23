// Build the self-contained customizer page (Node.js 22.13+, no packages):
//
//   node customizer/build.mjs --assets dist/assets --bulma node_modules/bulma/css/bulma.min.css \
//     --out dist/customizer/lumen-panel-customizer.html
//
// The page is one HTML file with everything inline: the token compiler (tokens/core.ts and
// tokens/keyhelp.ts with the types stripped), the four presets, the mock panel (customizer/mock.html),
// Bulma (MIT) and the gallery's layout skeleton standing in for the panel's own stylesheet, the
// built Lumen stylesheets, the Sora font and the Luminare logos. It makes no network request.
//
// --core-only prints just the compiler script (tests/parity runs it in a sandbox).

import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PRESETS = ["luminare", "graphite", "aurora", "contrast"];

/** core.ts + keyhelp.ts as one classic script that defines `LumenTokens`. */
export function coreScript() {
  const names = [];
  const parts = ["core.ts", "keyhelp.ts"].map((file) => {
    let js = stripTypeScriptTypes(readFileSync(join(root, "tokens", file), "utf8"), { mode: "strip" });
    js = js.replace(/^import [^;]*;\s*$/gm, "");
    js = js.replace(/^export (function|const|let) ([A-Za-z0-9_]+)/gm, (_m, kind, name) => {
      names.push(name);
      return `${kind} ${name}`;
    });
    if (/^\s*export\b/m.test(js)) throw new Error(`${file}: an export form the build does not handle`);
    return `// ---- tokens/${file} (types stripped) ----\n${js}`;
  });
  return (
    "(function (root) {\n\"use strict\";\n" + parts.join("\n") +
    `\nroot.LumenTokens = { ${names.join(", ")} };\n})(typeof window !== "undefined" ? window : globalThis);\n`
  );
}

function dataUrl(path, type) {
  return `data:${type};base64,${readFileSync(path).toString("base64")}`;
}

function json(value) {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

function build(args) {
  const assets = args.assets;
  const font = dataUrl(join(assets, "fonts", "Sora[wght].ttf"), "font/ttf");
  const css = (name) =>
    readFileSync(join(assets, name), "utf8").split('url("fonts/Sora%5Bwght%5D.ttf")').join(`url("${font}")`);
  const brand = {};
  for (const name of [
    "favicon.svg",
    "luminare-mark.svg",
    "luminare-mark-brand-deep.svg",
    "luminare-lockup-compact-light.svg",
    "luminare-lockup-compact-dark.svg",
    "luminare-lockup-horizontal-light.svg",
    "luminare-lockup-horizontal-dark.svg",
  ]) {
    brand[`brand/${name}`] = dataUrl(join(assets, "brand", name), "image/svg+xml");
  }
  const embedded = {
    bulma: readFileSync(args.bulma, "utf8").replace(/\/\*# sourceMappingURL=[^*]*\*\//g, ""),
    skeleton: readFileSync(join(root, "gallery", "src", "panel-skeleton.css"), "utf8"),
    css: { light: css("lumen.css"), dark: css("lumen-dark.css"), night: css("lumen-night.css") },
    brand,
  };
  const presets = Object.fromEntries(
    PRESETS.map((n) => [n, JSON.parse(readFileSync(join(root, "tokens", "presets", `${n}.json`), "utf8"))]),
  );
  const version = readFileSync(join(root, "version.txt"), "utf8").trim();
  const page = readFileSync(join(root, "customizer", "template.html"), "utf8")
    .replace("<!--@MOCK@-->", () => readFileSync(join(root, "customizer", "mock.html"), "utf8"))
    .replace("@VERSION@", () => version)
    .replace("/*@PRESETS@*/", () => json(presets))
    .replace("/*@ASSETS@*/", () => json(embedded))
    .replace("/*@CORE@*/", () => coreScript());
  if (/@[A-Z]+@/.test(page)) throw new Error("template.html: a placeholder was not filled");
  mkdirSync(dirname(args.out), { recursive: true });
  writeFileSync(args.out, page);
  console.log(`${args.out}  ${page.length} bytes`);
}

const argv = process.argv.slice(2);
if (argv.includes("--core-only")) {
  process.stdout.write(coreScript());
} else {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) args[argv[i].replace(/^--/, "")] = argv[i + 1];
  if (!args.assets || !args.bulma || !args.out) {
    console.error("usage: customizer/build.mjs --assets DIR --bulma FILE --out FILE");
    process.exit(2);
  }
  build(args);
}
