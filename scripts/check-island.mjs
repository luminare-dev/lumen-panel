// Check the built command palette (dist/assets/lumen-island.js) before it goes into a theme:
//
//   * one classic script (IIFE): no import/export statements, no dynamic import(), and no global
//     variable (vite's lib mode needs a name for IIFE builds; the entry exports nothing, so the
//     bundle must not start with "var <name> =");
//   * no network or storage APIs in the bundle, React included (fetch, XMLHttpRequest,
//     WebSocket, EventSource, sendBeacon, localStorage, sessionStorage, indexedDB, cookies);
//   * size: at most 80 KB after gzip (the number is printed; React 19 + React DOM are ~60 KB of it).
//
// Run: node scripts/check-island.mjs [--max-gzip-kb 80]

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const file = join(root, "dist", "assets", "lumen-island.js");
const flag = process.argv.indexOf("--max-gzip-kb");
const maxKb = flag > 0 ? Number(process.argv[flag + 1]) : 80;

const FORBIDDEN = [
  ["module syntax", /^\s*(?:import|export)\s[^;]*?(?:from\s*["']|[{*])/mu],
  ["dynamic import()", /\bimport\s*\(/u],
  ["fetch()", /\bfetch\s*\(/u],
  ["XMLHttpRequest", /\bXMLHttpRequest\b/u],
  ["WebSocket", /\bWebSocket\b/u],
  ["EventSource", /\bEventSource\b/u],
  ["sendBeacon", /\bsendBeacon\b/u],
  ["localStorage", /\blocalStorage\b/u],
  ["sessionStorage", /\bsessionStorage\b/u],
  ["indexedDB", /\bindexedDB\b/u],
  ["document.cookie", /\.cookie\b/u],
];

let code;
try {
  code = readFileSync(file, "utf8");
} catch {
  console.error(`${file}: missing; run 'npm run build:island' first`);
  process.exit(1);
}

const problems = FORBIDDEN.filter(([, re]) => re.test(code)).map(([name]) => `contains ${name}`);
if (!code.startsWith("/*! lumen-panel ")) problems.push("the licence banner is missing");
if (/^\/\*![^*]*\*\/\s*(?:var|let|const)\s+[\w$]+\s*=/u.test(code)) problems.push("declares a global variable");

const raw = Buffer.byteLength(code);
const gzip = gzipSync(code, { level: 9 }).length;
const kb = (n) => (n / 1024).toFixed(1);
console.log(`dist/assets/lumen-island.js: ${raw} bytes (${kb(raw)} KB), gzip ${gzip} bytes (${kb(gzip)} KB), limit ${maxKb} KB`);
if (gzip > maxKb * 1024) problems.push(`gzip size ${kb(gzip)} KB is above ${maxKb} KB`);

if (problems.length) {
  for (const p of problems) console.error(`lumen-island.js: ${p}`);
  process.exit(1);
}
console.log("ok: one classic script, no network or storage APIs");
