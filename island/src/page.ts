// What the island reads from the page around it: the panel's dark mode (body.dark-mode), the text
// direction and the language (<html dir lang>). The panel reloads the page when a user switches
// dark mode; the gallery switches without a reload, so the values are observed, not read once.

import { useEffect, useState } from "react";

export interface PageState {
  dark: boolean;
  dir: "ltr" | "rtl";
  lang: string;
}

export function readPage(doc: Document): PageState {
  const html = doc.documentElement;
  return {
    dark: Boolean(doc.body && doc.body.classList.contains("dark-mode")),
    dir: html.getAttribute("dir") === "rtl" ? "rtl" : "ltr",
    lang: html.getAttribute("lang") || "en",
  };
}

export function usePageState(doc: Document): PageState {
  const [state, setState] = useState(() => readPage(doc));
  useEffect(() => {
    const update = () =>
      setState((old) => {
        const next = readPage(doc);
        return old.dark === next.dark && old.dir === next.dir && old.lang === next.lang ? old : next;
      });
    const observer = new MutationObserver(update);
    observer.observe(doc.documentElement, { attributes: true, attributeFilter: ["dir", "lang"] });
    if (doc.body) observer.observe(doc.body, { attributes: true, attributeFilter: ["class"] });
    update();
    return () => observer.disconnect();
  }, [doc]);
  return state;
}

/** The focused element, looking into shadow roots (the palette's own trigger lives in one). */
export function deepActiveElement(doc: Document): Element | null {
  let el: Element | null = doc.activeElement;
  while (el && el.shadowRoot && el.shadowRoot.activeElement) el = el.shadowRoot.activeElement;
  return el;
}

export interface NavigatorLike {
  platform?: string;
  userAgent?: string;
  userAgentData?: { platform?: string };
}

/** Apple platforms show the Command key, all others Ctrl. */
export function isApplePlatform(nav: NavigatorLike | null | undefined): boolean {
  if (!nav) return false;
  return /mac|iphone|ipad|ipod/iu.test(nav.userAgentData?.platform || nav.platform || nav.userAgent || "");
}
