// Small inline icons for the gallery (the panel itself uses its own icon font). Drawn for this
// project: simple strokes on a 24px grid.
const PATHS = {
  gauge: "M4 15a8 8 0 1 1 16 0M12 15l4-5",
  server: "M4 5h16v6H4zM4 13h16v6H4zM8 8h.01M8 16h.01",
  globe: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18",
  mail: "M3 6h18v12H3zM3 7l9 6 9-6",
  table: "M4 5h16v14H4zM4 10h16M10 10v9",
  form: "M4 6h16M4 12h10M4 18h7",
  button: "M4 8h16v8H4zM9 12h6",
  tag: "M3 12V4h8l10 10-8 7z M7.5 8.5h.01",
  bell: "M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 20h4",
  tabs: "M3 9h18v11H3zM3 9V5h6v4M9 5h6v4",
  window: "M4 5h16v14H4zM4 9h16",
  palette: "M12 3a9 9 0 1 0 0 18c1.5 0 2-1 2-2s-1-1.5-1-2.5 1-1.5 2-1.5h2a4 4 0 0 0 4-4c0-4.5-4-8-9-8zM7.5 11h.01M10 7h.01M15 7h.01",
  login: "M10 17l5-5-5-5M15 12H3M14 4h6v16h-6",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20c1.5-4 4.5-6 8-6s6.5 2 8 6",
  sun: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
  direction: "M4 8h13l-3-3M20 16H7l3 3",
  check: "M5 12l5 5 9-10",
  warning: "M12 4l9 16H3zM12 10v4M12 17h.01",
  down: "M6 9l6 6 6-6",
  bars: "M4 7h16M4 12h16M4 17h16",
  power: "M12 3v8M6.5 6.5a8 8 0 1 0 11 0",
  search: "M11 4.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM16 16l4.5 4.5",
  square: "M4 2h16a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z",
};

const FILLED = new Set(["square"]);

export function Svg({ name, className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width="1em" height="1em" aria-hidden="true" focusable="false">
      {FILLED.has(name) ? (
        <path d={PATHS[name]} fill="currentColor" />
      ) : (
        <path d={PATHS[name]} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}

export function Icon({ name, size = "is-medium", className = "" }) {
  return (
    <span className={`icon ${size} ${className}`.trim()}>
      <Svg name={name} />
    </span>
  );
}
