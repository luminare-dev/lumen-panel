// The command palette island: one deferred IIFE script on the panel's internal pages.
//
// It renders into a shadow root on its own host element, so its styles cannot reach the panel
// and the panel's styles cannot reach it (only the inherited --lm-* design tokens pass through,
// which keeps it in the active light or dark mode). It makes no network requests and stores
// nothing: the entries are read from the page's own navigation each time it opens.

import { createRoot } from "react-dom/client";
import { collectEntries } from "./collect.js";
import { Palette } from "./Palette.jsx";
import css from "./palette.css?inline";

const HOST_ID = "lumen-command-palette";

function navigate(entry) {
  if (entry.newTab) window.open(entry.href, "_blank", "noopener,noreferrer");
  else window.location.assign(entry.href);
}

export function mount(doc = document) {
  if (doc.getElementById(HOST_ID) || !doc.getElementById("sidebar-navigation")) return null;
  const host = doc.createElement("div");
  host.id = HOST_ID;
  doc.body.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });
  const style = doc.createElement("style");
  style.textContent = css;
  const container = doc.createElement("div");
  shadow.append(style, container);
  const html = doc.documentElement;
  createRoot(container).render(
    <Palette
      getEntries={(t) => collectEntries(doc, { account: t.account })}
      lang={html.getAttribute("lang") || "en"}
      dir={html.getAttribute("dir") || "ltr"}
      navigate={navigate}
    />,
  );
  return host;
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => mount());
else mount();
