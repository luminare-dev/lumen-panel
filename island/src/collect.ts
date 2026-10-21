// Read the panel's own navigation from the page. Nothing is fetched and nothing is stored: the
// entries are rebuilt from the DOM every time the palette opens, so they always match what the
// signed-in user is allowed to see.
//
// Sources (markup of the panel's internal layout, see docs/keyhelp-markup.md):
//   #sidebar-navigation .app-menu-group   one group per sidebar section
//     .menu-label                         the group name
//     .menu-list a[href]                  its pages (a.is-active is the current page)
//   #header a[href*="return_to_admin"]    "back to administrator" while switched into a client
//   #user-menu a.dropdown-item[href]      profile, dark mode switch, logout

import type { Entry } from "./types";

const BLOCKED_SCHEMES = /^\s*(?:javascript|data|vbscript|file):/iu;

export function cleanText(node: Node | null | undefined): string {
  return node ? String(node.textContent ?? "").replace(/\s+/gu, " ").trim() : "";
}

/** Absolute URL for an href, or null if it must not be offered (empty, "#", script URLs). */
export function safeHref(href: string | null | undefined, baseURI: string): string | null {
  if (!href || href === "#" || BLOCKED_SCHEMES.test(href)) return null;
  try {
    const url = new URL(href, baseURI);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.href;
  } catch {
    return null;
  }
}

/** True on the panel's internal layout (every page after login); false on login and popups. */
export function isInternalLayout(doc: Document): boolean {
  return Boolean(doc.body && doc.getElementById("header") && doc.getElementById("sidebar-navigation"));
}

export function collectEntries(doc: Document, labels: { account: string } = { account: "Account" }): Entry[] {
  const entries: Entry[] = [];
  const seen = new Set<string>();
  const add = (anchor: Element, group: string, kind: "nav" | "account") => {
    const label = cleanText(anchor);
    const href = safeHref(anchor.getAttribute("href"), doc.baseURI);
    if (!label || !href) return;
    const key = `${href}\u0000${label}`;
    if (seen.has(key)) return;
    seen.add(key);
    entries.push({
      id: `e${entries.length}`,
      label,
      group,
      href,
      newTab: anchor.getAttribute("target") === "_blank",
      current: kind === "nav" && anchor.classList.contains("is-active"),
    });
  };
  for (const groupEl of doc.querySelectorAll("#sidebar-navigation .app-menu-group")) {
    const group = cleanText(groupEl.querySelector(".menu-label"));
    for (const a of groupEl.querySelectorAll(".menu-list a[href]")) add(a, group, "nav");
  }
  for (const a of doc.querySelectorAll('#header a[href*="return_to_admin"]')) add(a, labels.account, "account");
  for (const a of doc.querySelectorAll("#user-menu a.dropdown-item[href]")) add(a, labels.account, "account");
  return entries;
}
