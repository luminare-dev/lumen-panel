// Interface strings of the command palette. The panel's language comes from <html lang>.

export interface Strings {
  /** The language these strings are in (set as lang on the palette's own text). */
  code: string;
  title: string;
  placeholder: string;
  results: string;
  account: string;
  current: string;
  newTab: string;
  empty: string;
  count: (n: number) => string;
  move: string;
  open: string;
  close: string;
  closeLabel: string;
  button: string;
  buttonHidden: string;
}

const EN: Strings = {
  code: "en",
  title: "Go to a page",
  placeholder: "Search pages and settings",
  results: "Pages",
  account: "Account",
  current: "current page",
  newTab: "opens in a new tab",
  empty: "No page matches.",
  count: (n) => (n === 1 ? "1 page" : `${n} pages`),
  move: "move",
  open: "open",
  close: "close",
  closeLabel: "Close",
  button: "Search",
  buttonHidden: " pages",
};

const DE: Strings = {
  code: "de",
  title: "Zu einer Seite wechseln",
  placeholder: "Seiten und Einstellungen suchen",
  results: "Seiten",
  account: "Konto",
  current: "aktuelle Seite",
  newTab: "öffnet in einem neuen Tab",
  empty: "Keine Seite passt.",
  count: (n) => (n === 1 ? "1 Seite" : `${n} Seiten`),
  move: "wählen",
  open: "öffnen",
  close: "schließen",
  closeLabel: "Schließen",
  button: "Suchen",
  buttonHidden: " (Seiten)",
};

const STRINGS: Record<string, Strings> = { en: EN, de: DE };

/** The panel writes values like "zh_CN"; BCP 47 (the lang attribute) wants "zh-CN". */
export function bcp47(lang: string | null | undefined): string | undefined {
  const tag = String(lang || "").trim().replace(/_/gu, "-");
  return tag || undefined;
}

/** Strings for the panel language, English when there are none for it (check `code`). */
export function strings(lang: string | null | undefined): Strings {
  const key = String(lang || "en").toLowerCase().split(/[-_]/u)[0] ?? "en";
  return STRINGS[key] ?? EN;
}
