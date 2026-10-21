// The design-system gallery: a static React app that renders panel-like markup with Bulma 0.9.4
// (the CSS framework version the panel's default theme is built on) and the built Lumen CSS.
// dist/assets (stylesheets, island, fonts, logos) is served as the public folder, so the gallery
// loads lumen{-dark}{-rtl}.css and lumen-island.js exactly as the panel does.
// Build the stylesheets and the island first: npm run build:css && npm run build:island
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  base: "./",
  publicDir: fileURLToPath(new URL("../dist/assets", import.meta.url)),
  plugins: [react()],
  build: {
    outDir: fileURLToPath(new URL("../dist/gallery", import.meta.url)),
    emptyOutDir: true,
    sourcemap: false,
    target: ["chrome111", "edge111", "firefox121", "safari16.4"],
  },
});
