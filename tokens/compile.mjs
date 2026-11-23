// Compile a Lumen token file into a lumen-panel customization folder (Node.js 22.6+, no packages):
//
//   node --experimental-strip-types tokens/compile.mjs my.lumen.json --out custom/
//   node --experimental-strip-types tokens/compile.mjs --preset aurora --out /tmp/aurora
//
// The folder holds lumen.tokens.json (the checked, complete token set), override-follow.css (for
// Lumen, which follows KeyHelp's dark mode), override-dark.css (Lumen's dark stylesheets and Lumen
// Dark), branding.json (logos and favicon for the template patches) and README.txt. Uploaded files
// the tokens name as /storage/lumen/<file> go into its custom/ subfolder; the customizer ZIP adds
// them itself. Exit 1 when the token file has invalid values (they are listed and replaced by the
// Luminare default), 2 on a usage error.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { normalize } from "./core.ts";
import { brandingJson, compileKeyHelp } from "./keyhelp.ts";

const here = dirname(fileURLToPath(import.meta.url));
export const PRESET_NAMES = ["luminare", "graphite", "aurora", "contrast"];

export function preset(name) {
  return JSON.parse(readFileSync(join(here, "presets", `${name}.json`), "utf8"));
}

export function readme(tokens) {
  return (
    `Lumen customization for lumen-panel: ${tokens.meta.name.replace(/[^\x20-\x7e]/g, "")}\n\n` +
    "Install on the panel server (dry run first, then with --yes):\n" +
    "  python3 -m lumen_panel apply-custom --zip <this ZIP> --keyhelp /home/keyhelp/www/keyhelp --variant all\n\n" +
    "Contents: lumen.tokens.json (the token file; import it in the customizer to edit it again),\n" +
    "override-follow.css and override-dark.css (compiled from the tokens), branding.json and the\n" +
    "uploaded files in custom/. No KeyHelp file is included.\n" +
    "https://github.com/luminare-dev/lumen-panel\n"
  );
}

/** The files of a customization folder (without uploads), keyed by relative path. */
export function customizationFiles(tokens) {
  return {
    "lumen.tokens.json": `${JSON.stringify(tokens, null, 2)}\n`,
    "override-follow.css": compileKeyHelp(tokens, "follow"),
    "override-dark.css": compileKeyHelp(tokens, "dark"),
    "branding.json": brandingJson(tokens),
    "README.txt": readme(tokens),
  };
}

function main(argv) {
  let input = null;
  let out = null;
  let presetName = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--out") out = argv[++i];
    else if (argv[i] === "--preset") presetName = argv[++i];
    else if (!input) input = argv[i];
    else return usage(`unexpected argument ${argv[i]}`);
  }
  if (!out || Boolean(input) === Boolean(presetName)) return usage("give a token file or --preset, and --out");
  if (presetName && !PRESET_NAMES.includes(presetName)) return usage(`unknown preset ${presetName}`);
  let doc;
  try {
    doc = presetName ? preset(presetName) : JSON.parse(readFileSync(input, "utf8"));
  } catch (err) {
    return usage(`cannot read ${input}: ${err.message}`);
  }
  const { tokens, errors } = normalize(doc, preset("luminare"));
  mkdirSync(out, { recursive: true });
  for (const [name, text] of Object.entries(customizationFiles(tokens))) writeFileSync(join(out, name), text);
  for (const path of errors) console.error(`replaced by the default: ${path}`);
  console.log(`${out}: ${tokens.meta.name}`);
  return errors.length ? 1 : 0;
}

function usage(message) {
  console.error(`error: ${message}\nusage: tokens/compile.mjs (TOKENS.json | --preset NAME) --out DIR`);
  return 2;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) process.exit(main(process.argv.slice(2)));
