// Interface strings of the command palette. The panel's language comes from <html lang>.

export interface Strings {
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

export function strings(lang: string | null | undefined): Strings {
  const key = String(lang || "en").toLowerCase().split(/[-_]/u)[0] ?? "en";
  return STRINGS[key] ?? EN;
}
