// The command palette: a modal dialog with a search field and a list of the panel's pages.
//
// Accessibility pattern: role="dialog" with aria-modal; the search field is a combobox that
// controls a listbox and points at the highlighted option with aria-activedescendant, so focus
// stays in the field while the arrow keys move through the results. Tab and Shift+Tab cycle
// between the field and the close button (focus trap); focus that escapes (a click, a script)
// is brought back. Closing returns focus to where it was before the palette opened.

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, MouseEvent as ReactMouseEvent } from "react";
import { createPortal } from "react-dom";
import { highlight, search } from "./fuzzy";
import { bcp47, strings } from "./i18n";
import { deepActiveElement, isApplePlatform, usePageState, type NavigatorLike } from "./page";
import type { Entry } from "./types";

// Keyboard shortcuts inside these elements belong to the editor (CodeMirror, Trumbowyg).
const EDITOR_SELECTOR = ".CodeMirror, .cm-editor, .trumbowyg-box, [contenteditable=''], [contenteditable='true']";
const PAGE_STEP = 8;
const MAX_RESULTS = 50;

type ShortcutEvent = Pick<KeyboardEvent, "ctrlKey" | "metaKey" | "altKey" | "shiftKey" | "key" | "code">;

/**
 * Cmd+K on Apple platforms, Ctrl+K elsewhere. On a Mac, Ctrl+K stays with text fields (delete to
 * the end of the line). The physical K key also counts when the layout types a non-Latin letter
 * there (Russian, Arabic), but not on Latin layouts that put another letter on it (Dvorak).
 */
export function isToggleKey(event: ShortcutEvent, apple: boolean): boolean {
  const mod = apple ? event.metaKey && !event.ctrlKey : event.ctrlKey && !event.metaKey;
  if (!mod || event.altKey || event.shiftKey) return false;
  const key = String(event.key || "").toLowerCase();
  return key === "k" || (event.code === "KeyK" && !/^[a-z]$/u.test(key));
}

function inEditor(event: Event): boolean {
  const target = event.composedPath ? event.composedPath()[0] : event.target;
  return target instanceof Element && target.closest(EDITOR_SELECTOR) !== null;
}

function SearchIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="m16 16 4.5 4.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export interface PaletteProps {
  /** Reads the entries each time the palette opens. */
  getEntries: (labels: { account: string }) => Entry[];
  /** Opens an entry (the island uses location.assign or window.open). */
  navigate: (entry: Entry) => void;
  /** Where the header button is rendered (a node in its own shadow root), if anywhere. */
  triggerContainer?: Element | DocumentFragment | null;
  doc?: Document;
}

export function Palette({ getEntries, navigate, triggerContainer = null, doc = document }: PaletteProps) {
  const page = usePageState(doc);
  const t = strings(page.lang);
  const pageLang = bcp47(page.lang);
  const apple = useMemo(() => isApplePlatform(globalThis.navigator as NavigatorLike | undefined), []);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [entries, setEntries] = useState<Entry[]>([]);
  const openRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<Element | null>(null);
  const uid = `lmp${useId().replace(/[^A-Za-z0-9_-]/gu, "")}`;
  const ids = { title: `${uid}-title`, list: `${uid}-list`, status: `${uid}-status` };

  // Without a query every entry is listed (a long admin sidebar must not be cut off).
  const results = useMemo(() => search(entries, query, query.trim() ? MAX_RESULTS : Infinity), [entries, query]);
  const count = results.length;
  const current = Math.min(active, Math.max(count - 1, 0));

  const show = useCallback(
    (from?: Element | null) => {
      returnFocus.current = from ?? deepActiveElement(doc);
      openRef.current = true;
      let list: Entry[] = [];
      try {
        list = getEntries({ account: t.account });
      } catch (error) {
        console.warn("lumen-panel: could not read the panel's navigation", error);
      }
      setEntries(list);
      setQuery("");
      setActive(0);
      setOpen(true);
    },
    [doc, getEntries, t.account],
  );

  const hide = useCallback(() => {
    openRef.current = false;
    setOpen(false);
    const el = returnFocus.current;
    returnFocus.current = null;
    if (el instanceof HTMLElement && el.isConnected) el.focus();
  }, []);

  const go = useCallback(
    (entry: Entry | undefined) => {
      if (!entry) return;
      hide();
      navigate(entry);
    },
    [hide, navigate],
  );

  // Ctrl+K / Cmd+K anywhere on the page, except inside a code or text editor.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.isComposing || !isToggleKey(event, apple) || inEditor(event)) return;
      event.preventDefault();
      if (openRef.current) hide();
      else show();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [show, hide, apple]);

  // The page behind the dialog does not scroll while it is open (restored on close and unmount).
  useEffect(() => {
    if (!open) return undefined;
    const style = doc.documentElement.style;
    const before = [style.getPropertyValue("overflow"), style.getPropertyValue("scrollbar-gutter")] as const;
    style.setProperty("overflow", "hidden");
    style.setProperty("scrollbar-gutter", "stable");
    return () => {
      style.setProperty("overflow", before[0]);
      style.setProperty("scrollbar-gutter", before[1]);
    };
  }, [open, doc]);

  // Focus moves into the dialog on open, and back into it if anything moves it out.
  useEffect(() => {
    if (!open) return undefined;
    inputRef.current?.focus();
    const onFocusIn = (event: FocusEvent) => {
      const dialog = dialogRef.current;
      if (!openRef.current || !dialog || event.composedPath().includes(dialog)) return;
      inputRef.current?.focus();
    };
    doc.addEventListener("focusin", onFocusIn, true);
    return () => doc.removeEventListener("focusin", onFocusIn, true);
  }, [open, doc]);

  useEffect(() => {
    const option = listRef.current?.querySelector(`[data-index="${current}"]`);
    if (option && typeof option.scrollIntoView === "function") option.scrollIntoView({ block: "nearest" });
  }, [current, results]);

  const onKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    // Keys typed here belong to the palette, not to the panel's own keyboard handlers.
    event.stopPropagation();
    // While an input method composes (pinyin, kana), Enter and Escape belong to it.
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    const move = (to: number) => {
      event.preventDefault();
      if (count) setActive(to);
    };
    switch (event.key) {
      case "ArrowDown":
        move((current + 1) % Math.max(count, 1));
        break;
      case "ArrowUp":
        move((current - 1 + count) % Math.max(count, 1));
        break;
      case "PageDown":
        move(Math.min(current + PAGE_STEP, count - 1));
        break;
      case "PageUp":
        move(Math.max(current - PAGE_STEP, 0));
        break;
      case "Enter":
        if (event.target !== inputRef.current) break; // the close button handles its own Enter
        event.preventDefault();
        go(results[current]?.entry);
        break;
      case "Escape":
        event.preventDefault();
        hide();
        break;
      case "Tab": {
        const stops = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>("input, button") ?? []);
        if (stops.length === 0) break;
        event.preventDefault();
        const at = stops.indexOf(event.target as HTMLElement);
        const next = event.shiftKey ? (at <= 0 ? stops.length - 1 : at - 1) : (at + 1) % stops.length;
        stops[next]?.focus();
        break;
      }
      default:
        break;
    }
  };

  // A click on the dialog's text must not take focus away from the search field.
  const keepFocus = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (event.target !== inputRef.current) event.preventDefault();
  };

  const rootClass = page.dark ? "lm is-dark" : "lm";

  const trigger =
    triggerContainer &&
    createPortal(
      <div className={rootClass} dir={page.dir} lang={t.code}>
        <button
          ref={triggerRef}
          type="button"
          className="trigger"
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-keyshortcuts={apple ? "Meta+K" : "Control+K"}
          onClick={() => (openRef.current ? hide() : show(triggerRef.current))}
        >
          <SearchIcon />
          <span className="trigger-label">
            {t.button}
            <span className="visually-hidden">{t.buttonHidden}</span>
          </span>
          <kbd aria-hidden="true">{apple ? "⌘ K" : "Ctrl K"}</kbd>
        </button>
      </div>,
      triggerContainer,
    );

  if (!open) return trigger || null;

  return (
    <>
      {trigger}
      <div className={rootClass}>
        <div
          className="backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) hide();
          }}
        >
          <div
            ref={dialogRef}
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={ids.title}
            dir={page.dir}
            lang={t.code}
            onKeyDown={onKeyDown}
            onMouseDown={keepFocus}
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
                aria-label={t.placeholder}
                placeholder={t.placeholder}
                autoComplete="off"
                spellCheck={false}
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setActive(0);
                }}
              />
              <button type="button" className="close" aria-label={`${t.closeLabel} (Esc)`} onClick={hide}>
                <kbd aria-hidden="true">Esc</kbd>
              </button>
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
                  <span className="label" lang={pageLang}>
                    {highlight(entry.label, indices).map((part, i) =>
                      part.hit ? <mark key={i}>{part.text}</mark> : <span key={i}>{part.text}</span>,
                    )}
                  </span>
                  {entry.current && (
                    <span className="badge">
                      <span className="visually-hidden">, </span>
                      {t.current}
                    </span>
                  )}
                  {entry.newTab && <span className="visually-hidden">, {t.newTab}</span>}
                  {entry.group && (
                    <span className="group" lang={entry.group === t.account ? t.code : pageLang}>
                      <span className="visually-hidden">, </span>
                      {entry.group}
                    </span>
                  )}
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
      </div>
    </>
  );
}
