// Build the command palette as one IIFE file: dist/assets/lumen-island.js.
// React is bundled in (production build); the stylesheet is inlined as a string for the shadow
// roots. No code splitting, no dynamic imports, no network requests at run time
// (scripts/check-island.mjs checks the built file).
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));

export default defineConfig({
  root,
  publicDir: false,
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir: "dist/assets",
    emptyOutDir: false,
    copyPublicDir: false,
    sourcemap: false,
    minify: true,
    target: ["chrome111", "edge111", "firefox121", "safari16.4"],
    lib: {
      entry: "island/src/main.ts",
      name: "LumenIsland",
      formats: ["iife"],
      fileName: () => "lumen-island.js",
    },
    rolldownOptions: {
      output: {
        banner:
          `/*! lumen-panel ${pkg.version} command palette | MIT | ` +
          "https://github.com/luminare-dev/lumen-panel | includes React and React DOM " +
          "(MIT, Copyright (c) Meta Platforms, Inc. and affiliates) */",
      },
    },
  },
});
