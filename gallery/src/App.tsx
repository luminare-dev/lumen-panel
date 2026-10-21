// The gallery shell mirrors the panel's internal layout (#header, #user-menu, #sidebar,
// #content, #footer) and switches stylesheets the way the panel does: lumen{-dark}{-rtl}.css
// plus body.dark-mode and <html dir>. Each sidebar link is a page (hash route).
// The start state can be set in the URL, for screenshots: ?mode=dark&dir=rtl#forms
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Icon, Svg, type IconName } from "./parts";
import { Buttons, Cards, Forms, Modals, Notifications, Pagination, Tables, Tabs, Tags } from "./pages/Components";
import { Shell, Tokens, Typography } from "./pages/Foundations";
import { Dashboard, Login } from "./pages/Screens";

type Mode = "light" | "dark";
type Dir = "ltr" | "rtl";

interface Ctx {
  mode: Mode;
  styleTick: number;
  openUserMenu: () => void;
}

interface PageDef {
  id: string;
  label: string;
  render: (ctx: Ctx) => ReactNode;
}

const NAV: { label: string; icon: IconName; pages: PageDef[] }[] = [
  {
    label: "Foundations",
    icon: "palette",
    pages: [
      { id: "tokens", label: "Design tokens", render: (c) => <Tokens mode={c.mode} styleTick={c.styleTick} /> },
      { id: "typography", label: "Typography", render: () => <Typography /> },
      { id: "shell", label: "App shell", render: (c) => <Shell onOpenUserMenu={c.openUserMenu} /> },
    ],
  },
  {
    label: "Components",
    icon: "window",
    pages: [
      { id: "cards", label: "Cards", render: () => <Cards /> },
      { id: "tables", label: "Tables", render: () => <Tables /> },
      { id: "pagination", label: "Pagination", render: () => <Pagination /> },
      { id: "forms", label: "Forms", render: () => <Forms /> },
      { id: "buttons", label: "Buttons", render: () => <Buttons /> },
      { id: "tags", label: "Tags", render: () => <Tags /> },
      { id: "notifications", label: "Notifications", render: () => <Notifications /> },
      { id: "modals", label: "Modals and overlays", render: () => <Modals /> },
      { id: "tabs", label: "Tabs", render: () => <Tabs /> },
    ],
  },
  {
    label: "Screens",
    icon: "pages",
    pages: [
      { id: "dashboard", label: "Dashboard", render: () => <Dashboard /> },
      { id: "login", label: "Login page", render: (c) => <Login dark={c.mode === "dark"} /> },
    ],
  },
];

const PAGES = NAV.flatMap((group) => group.pages.map((page) => ({ ...page, group: group.label })));
const DEFAULT_PAGE = "dashboard";

function pageFromHash(): string {
  const id = window.location.hash.replace(/^#/u, "");
  return PAGES.some((p) => p.id === id) ? id : DEFAULT_PAGE;
}

function initial<T extends string>(name: string, allowed: readonly T[], fallback: T): T {
  const value = new URLSearchParams(window.location.search).get(name);
  return (allowed as readonly string[]).includes(value ?? "") ? (value as T) : fallback;
}

export interface Stylesheets {
  ltr: string;
  rtl: string;
}

export function App({ bulma }: { bulma: Stylesheets }) {
  const [mode, setMode] = useState<Mode>(() => initial("mode", ["light", "dark"] as const, "light"));
  const [dir, setDir] = useState<Dir>(() => initial("dir", ["ltr", "rtl"] as const, "ltr"));
  const [pageId, setPageId] = useState(pageFromHash);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [styleTick, setStyleTick] = useState(0);
  const dark = mode === "dark";
  const rtl = dir === "rtl";
  const page = PAGES.find((p) => p.id === pageId) ?? PAGES[0]!;

  // Switch the stylesheets like the panel does; count each load so token readers refresh.
  useEffect(() => {
    document.body.className = dark ? "dark-mode" : "default-mode";
    document.documentElement.setAttribute("dir", dir);
    document.querySelector('meta[name="color-scheme"]')?.setAttribute("content", dark ? "dark" : "light");
    const bump = () => setStyleTick((t) => t + 1);
    const links = [
      [document.getElementById("bulma-css"), rtl ? bulma.rtl : bulma.ltr],
      [document.getElementById("lumen-css"), `./lumen${dark ? "-dark" : ""}${rtl ? "-rtl" : ""}.css`],
    ] as const;
    for (const [link, href] of links) {
      if (!link || link.getAttribute("href") === href) continue;
      link.addEventListener("load", bump, { once: true });
      link.setAttribute("href", href);
    }
    bump();
  }, [dark, dir, rtl, bulma]);

  useEffect(() => {
    const onHash = () => {
      setPageId(pageFromHash());
      setSidebarOpen(false);
      setUserMenuOpen(false);
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onHash);
    // The real command palette, loaded like the panel loads it: one deferred script.
    if (!document.getElementById("lumen-island-script")) {
      const script = document.createElement("script");
      script.id = "lumen-island-script";
      script.defer = true;
      script.src = "./lumen-island.js";
      document.body.appendChild(script);
    }
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    document.title = `${page.label} | Lumen gallery`;
  }, [page.label]);

  const clock = useMemo(() => new Date().toISOString().slice(11, 16), []);
  const ctx: Ctx = { mode, styleTick, openUserMenu: () => setUserMenuOpen(true) };

  return (
    <>
      <a className="gallery-skip" href="#content">
        Skip to the content
      </a>
      <header id="header">
        <nav id="top-nav" aria-label="Gallery">
          <div className="level is-mobile">
            <div className="level-left">
              <a className="level-item" href={`#${DEFAULT_PAGE}`}>
                <figure>
                  <img
                    className="lumen-logo lumen-logo--header"
                    src={`./brand/luminare-lockup-compact-${dark ? "dark" : "light"}.svg`}
                    width="127"
                    height="42"
                    alt="Luminare Development"
                  />
                </figure>
              </a>
              <div className="level-item is-hidden-touch has-padding-left-medium has-text-grey">
                Lumen gallery | <span className="has-margin-left-xsmall">{clock}</span>
              </div>
            </div>
            <div className="level-left">
              {/* Below 769px these two move into the user menu, so the header fits a 320px screen. */}
              <button className="button level-item is-hidden-mobile" type="button" aria-pressed={dark} onClick={() => setMode(dark ? "light" : "dark")}>
                <Icon name="moon" />
                <span>Dark mode</span>
              </button>
              <button className="button level-item is-hidden-mobile" type="button" aria-pressed={rtl} onClick={() => setDir(rtl ? "ltr" : "rtl")}>
                <Icon name="direction" />
                <span>Right to left</span>
              </button>
              <a
                id="app-user-menu-toggle"
                className="level-item"
                href="#user-menu"
                aria-expanded={userMenuOpen}
                aria-controls="user-menu"
                onClick={(event) => {
                  event.preventDefault();
                  setUserMenuOpen(!userMenuOpen);
                }}
              >
                <span className="icon is-large">
                  <span className="fa-stack fa-1x">
                    <Svg name="square" className={`fa fa-square fa-stack-2x${dark ? " has-text-link" : ""}`} />
                    <Svg name="user" className="fa fa-user fa-stack-1x fa-inverse" />
                  </span>
                </span>
                <span className="is-sr-only">User menu</span>
                <span className="is-hidden-mobile">admin</span>
              </a>
              <a
                id="app-sidebar-toggle"
                className="level-item is-hidden-desktop"
                href="#sidebar"
                aria-expanded={sidebarOpen}
                aria-controls="sidebar"
                onClick={(event) => {
                  event.preventDefault();
                  setSidebarOpen(!sidebarOpen);
                }}
              >
                <Icon name="bars" size="is-large" />
                <span className="is-sr-only">Menu</span>
              </a>
            </div>
          </div>
        </nav>
      </header>

      <div id="user-menu" className={userMenuOpen ? undefined : "is-hidden"}>
        <a className="dropdown-item" href="#shell">
          Profile (example)
        </a>
        <button className="dropdown-item gallery-menu-button" type="button" onClick={() => setMode(dark ? "light" : "dark")}>
          {dark ? "Light mode" : "Dark mode"}
        </button>
        <button className="dropdown-item gallery-menu-button" type="button" onClick={() => setDir(rtl ? "ltr" : "rtl")}>
          {rtl ? "Left to right" : "Right to left"}
        </button>
        <hr className="dropdown-divider" />
        <a className="dropdown-item" href="#login">
          Log out (example)
        </a>
      </div>

      <section id="sidebar" className={sidebarOpen ? "is-active" : undefined} aria-label="Pages">
        <nav id="sidebar-navigation" className="menu has-margin-x-xsmall">
          {NAV.map((group) => (
            <div className="app-menu-group has-margin-bottom-medium" key={group.label}>
              <p className="menu-label has-margin-bottom-small">
                <Icon name={group.icon} />
                {group.label}
              </p>
              <ul className="menu-list">
                {group.pages.map((p) => (
                  <li key={p.id}>
                    <a href={`#${p.id}`} className={p.id === page.id ? "is-active" : undefined} aria-current={p.id === page.id ? "page" : undefined}>
                      <small>
                        <span className="icon is-small">
                          <Svg name="chevron" />
                        </span>
                      </small>{" "}
                      {p.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </section>
      <div id="sidebar-overlay" className={sidebarOpen ? "is-active" : undefined} onClick={() => setSidebarOpen(false)} />

      <section id="content-wrapper">
        <main id="content" tabIndex={-1}>
          <nav className="breadcrumb is-small has-margin-bottom-none" aria-label="breadcrumbs">
            <ul>
              <li>
                <a href={`#${DEFAULT_PAGE}`}>Lumen</a>
              </li>
              <li>
                <a href={`#${page.id}`}>{page.group}</a>
              </li>
              <li className="is-active">
                <a href={`#${page.id}`} aria-current="page">
                  {page.label}
                </a>
              </li>
            </ul>
          </nav>
          <div className="content-title">
            <h1 className="title is-4">{page.label}</h1>
          </div>
          {page.render(ctx)}
        </main>
        <footer id="footer">
          <div className="content has-text-centered">
            <p>
              lumen-panel, a Luminare Development open-source project. Not affiliated with or endorsed by Keyweb AG. KeyHelp is a
              registered trademark of Keyweb AG.
            </p>
            <p className="is-size-7">
              Showing {mode} mode, {rtl ? "right to left" : "left to right"}. Example data only.
            </p>
          </div>
        </footer>
      </section>
    </>
  );
}
