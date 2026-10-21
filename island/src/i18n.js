// Interface strings of the command palette. The panel's language comes from <html lang>.

const STRINGS = {
  en: {
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
  },
  de: {
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
  },
};

export function strings(lang) {
  const key = String(lang || "en").toLowerCase().split(/[-_]/u)[0];
  return STRINGS[key] || STRINGS.en;
}
