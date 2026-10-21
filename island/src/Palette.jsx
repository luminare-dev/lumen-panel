import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { highlight, search } from "./fuzzy.js";
import { strings } from "./i18n.js";

// Keyboard shortcuts inside these elements belong to the editor (CodeMirror, Trumbowyg).
const EDITOR_SELECTOR = ".CodeMirror, .cm-editor, .trumbowyg-box, [contenteditable=''], [contenteditable='true']";

function isToggleKey(event) {
  return (event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && String(event.key || "").toLowerCase() === "k";
}

function inEditor(event) {
  const target = event.composedPath ? event.composedPath()[0] : event.target;
  return Boolean(target && target.closest && target.closest(EDITOR_SELECTOR));
}

function SearchIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="m16 16 4.5 4.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Palette({ getEntries, lang, dir, navigate, initiallyOpen = false }) {
  const t = strings(lang);
  const [open, setOpen] = useState(initiallyOpen);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [entries, setEntries] = useState(() => (initiallyOpen ? getEntries(t) : []));
  const [textDir, setTextDir] = useState(dir);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const returnFocus = useRef(null);
  const uid = useId().replace(/:/gu, "");
  const ids = { title: `${uid}-title`, list: `${uid}-list`, status: `${uid}-status` };

  const results = useMemo(() => search(entries, query), [entries, query]);

  const show = useCallback(() => {
    returnFocus.current = document.activeElement;
    setTextDir(document.documentElement.getAttribute("dir") || dir);
    setEntries(getEntries(t));
    setQuery("");
    setActive(0);
    setOpen(true);
  }, [getEntries, t, dir]);

  const hide = useCallback(() => {
    setOpen(false);
    const el = returnFocus.current;
    returnFocus.current = null;
    if (el && typeof el.focus === "function" && document.contains(el)) el.focus();
  }, []);

  const go = useCallback(
    (entry) => {
      if (!entry) return;
      setOpen(false);
      navigate(entry);
    },
    [navigate],
  );

  // Ctrl+K / Cmd+K anywhere on the page, except inside a code or text editor.
  useEffect(() => {
    const onKey = (event) => {
      if (!isToggleKey(event) || inEditor(event)) return;
      event.preventDefault();
      if (open) hide();
      else show();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open, show, hide]);

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus();
  }, [open]);

  useEffect(() => {
    const list = listRef.current;
    const option = list && list.querySelector(`[data-index="${active}"]`);
    if (option && option.scrollIntoView) option.scrollIntoView({ block: "nearest" });
  }, [active, results]);

  if (!open) return null;

  const count = results.length;
  const current = Math.min(active, Math.max(count - 1, 0));

  const onKeyDown = (event) => {
    // Keys typed here belong to the palette, not to the panel's own keyboard handlers.
    event.stopPropagation();
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        if (count) setActive((current + 1) % count);
        break;
      case "ArrowUp":
        event.preventDefault();
        if (count) setActive((current - 1 + count) % count);
        break;
      case "PageDown":
        event.preventDefault();
        if (count) setActive(Math.min(current + 8, count - 1));
        break;
      case "PageUp":
        event.preventDefault();
        if (count) setActive(Math.max(current - 8, 0));
        break;
      case "Enter":
        event.preventDefault();
        go(results[current] && results[current].entry);
        break;
      case "Escape":
        event.preventDefault();
        hide();
        break;
      case "Tab":
        // The search field is the only focus stop; options are reached with the arrow keys.
        event.preventDefault();
        break;
      default:
        break;
    }
  };

  return (
    <div className="backdrop" onMouseDown={hide}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={ids.title}
        dir={textDir || undefined}
        lang={lang || undefined}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 id={ids.title} className="visually-hidden">
          {t.title}
        </h2>
        <div className="search">
          <SearchIcon />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls={ids.list}
            aria-autocomplete="list"
            aria-activedescendant={count ? `${uid}-opt-${current}` : undefined}
            aria-describedby={ids.status}
            placeholder={t.placeholder}
            autoComplete="off"
            spellCheck="false"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
          />
          <kbd aria-hidden="true">Esc</kbd>
        </div>
        <ul id={ids.list} ref={listRef} className="results" role="listbox" aria-label={t.results}>
          {results.map(({ entry, indices }, index) => (
            <li
              key={entry.id}
              id={`${uid}-opt-${index}`}
              data-index={index}
              role="option"
              aria-selected={index === current}
              className={index === current ? "option is-active" : "option"}
              onMouseMove={() => index !== current && setActive(index)}
              onClick={() => go(entry)}
            >
              <span className="label">
                {highlight(entry.label, indices).map((part, i) =>
                  part.hit ? <mark key={i}>{part.text}</mark> : <span key={i}>{part.text}</span>,
                )}
              </span>
              {entry.current && <span className="badge">{t.current}</span>}
              {entry.newTab && <span className="visually-hidden">, {t.newTab}</span>}
              {entry.group && <span className="group">{entry.group}</span>}
            </li>
          ))}
        </ul>
        {count === 0 && <p className="empty">{t.empty}</p>}
        <p id={ids.status} className="visually-hidden" role="status" aria-live="polite">
          {t.count(count)}
        </p>
        <p className="hint" aria-hidden="true">
          <span>
            <kbd>↑</kbd> <kbd>↓</kbd> {t.move}
          </span>
          <span>
            <kbd>Enter</kbd> {t.open}
          </span>
          <span>
            <kbd>Esc</kbd> {t.close}
          </span>
        </p>
      </div>
    </div>
  );
}
