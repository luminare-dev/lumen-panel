// Entry of the island build (dist/assets/lumen-island.js, one IIFE loaded with defer).
// The script is only added to the internal layout by the patch set; mount() checks the layout
// again, so the file does nothing on any other page. A failure is logged, never thrown: the
// panel must keep working without the palette.

import { mount } from "./mount";

function start(): void {
  try {
    mount(document);
  } catch (error) {
    console.warn("lumen-panel: command palette not started", error);
  }
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
else start();
