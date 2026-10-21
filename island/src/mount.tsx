// Mount the command palette on the panel's internal layout.
//
// Everything the island draws lives in shadow roots on its own host elements, so its styles
// cannot reach the panel and the panel's styles (Bulma, jQuery plugins) cannot reach it. Only
// the inherited --lm-* design tokens pass through, which keeps it in the active light or dark
// mode. It makes no network requests and stores nothing: the entries are read from the page's
// own navigation each time the palette opens.

import { createRoot, type Root } from "react-dom/client";
import { collectEntries, isInternalLayout } from "./collect";
import { Palette } from "./Palette";
import type { Entry } from "./types";
import css from "./palette.css?inline";

export const HOST_ID = "lumen-command-palette";
export const TRIGGER_ID = "lumen-command-palette-trigger";

export interface Mounted {
  host: HTMLElement;
  trigger: HTMLElement | null;
  root: Root;
  unmount: () => void;
}

function navigate(entry: Entry): void {
  if (entry.newTab) window.open(entry.href, "_blank", "noopener,noreferrer");
  else window.location.assign(entry.href);
}

function shadowContainer(doc: Document, host: HTMLElement): HTMLElement {
  const shadow = host.attachShadow({ mode: "open" });
  const style = doc.createElement("style");
  style.textContent = css;
  const container = doc.createElement("div");
  shadow.append(style, container);
  return container;
}

/**
 * The header button goes right before the user menu toggle, in the same flex row, so it lines up
 * with the panel's own header items. Without that toggle the palette still opens with Ctrl+K.
 */
function mountTrigger(doc: Document): { host: HTMLElement; container: HTMLElement } | null {
  const anchor = doc.querySelector("#header #app-user-menu-toggle");
  const parent = anchor?.parentElement;
  if (!anchor || !parent) return null;
  const host = doc.createElement("div");
  host.id = TRIGGER_ID;
  host.className = "level-item";
  parent.insertBefore(host, anchor);
  return { host, container: shadowContainer(doc, host) };
}

export function mount(doc: Document = document, go: (entry: Entry) => void = navigate): Mounted | null {
  if (!isInternalLayout(doc) || doc.getElementById(HOST_ID)) return null;
  const host = doc.createElement("div");
  host.id = HOST_ID;
  doc.body.appendChild(host);
  const container = shadowContainer(doc, host);
  const trigger = mountTrigger(doc);
  const root = createRoot(container);
  root.render(
    <Palette
      doc={doc}
      getEntries={(labels) => collectEntries(doc, labels)}
      navigate={go}
      triggerContainer={trigger?.container ?? null}
    />,
  );
  return {
    host,
    trigger: trigger?.host ?? null,
    root,
    unmount() {
      root.unmount();
      host.remove();
      trigger?.host.remove();
    },
  };
}
