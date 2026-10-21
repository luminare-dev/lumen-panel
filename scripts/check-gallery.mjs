// After the gallery build: put the licence files next to the static gallery and check that the
// bundled third-party code keeps its notice (gallery/dist is published as a CI artifact):
//
//   * copies LICENSE, NOTICE and THIRD_PARTY_NOTICES.md into gallery/dist/;
//   * every gallery/dist/assets/*.js starts with the lumen-panel gallery banner, which names
//     React and React DOM (MIT); Bulma's CSS keeps its own banner (checked for its name).
//
// Run: node scripts/check-gallery.mjs (part of npm run build:gallery)

import { copyFileSync, existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "gallery", "dist");
const assets = join(dist, "assets");
const problems = [];

if (!existsSync(assets)) {
  console.error(`${assets}: missing; run 'npm run build:gallery' first`);
  process.exit(1);
}

for (const name of ["LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"]) copyFileSync(join(root, name), join(dist, name));

const files = readdirSync(assets);
const scripts = files.filter((f) => f.endsWith(".js"));
if (scripts.length === 0) problems.push("no JavaScript in gallery/dist/assets");
for (const file of scripts) {
  const code = readFileSync(join(assets, file), "utf8");
  if (!code.startsWith("/*! lumen-panel gallery ") || !code.slice(0, 400).includes("React")) {
    problems.push(`${file}: the licence banner naming React is missing`);
  }
}
for (const file of files.filter((f) => f.endsWith(".css") && f.toLowerCase().includes("bulma"))) {
  if (!readFileSync(join(assets, file), "utf8").slice(0, 300).includes("bulma")) problems.push(`${file}: Bulma's banner is missing`);
}

if (problems.length) {
  for (const p of problems) console.error(`gallery: ${p}`);
  process.exit(1);
}
console.log(`ok: gallery/dist has LICENSE, NOTICE and THIRD_PARTY_NOTICES.md; ${scripts.length} script(s) carry the banner`);
