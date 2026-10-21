// The gallery shell mirrors the panel's internal layout (#header, #sidebar, #content) and switches
// stylesheets the way the panel does: lumen{-dark}{-rtl}.css plus body.dark-mode / <html dir>.
// Start state can be set in the URL for screenshots: ?mode=dark&dir=rtl
import { useEffect, useMemo, useState } from "react";
import { Svg } from "./Icon.jsx";
import { Buttons, Dashboard, Forms, Icon, Login, Messages, Overlays, Tables, Tabs, Tags } from "./Sections.jsx";
import { Tokens } from "./Tokens.jsx";

const NAV = [
  {
    label: "Overview",
    icon: "gauge",
    items: [
      ["Dashboard", "#dashboard"],
      ["Design tokens", "#tokens"],
    ],
  },
  {
    label: "Components",
    icon: "palette",
    items: [
      ["Tables and pagination", "#tables"],
      ["Forms", "#forms"],
      ["Buttons", "#buttons"],
      ["Tags", "#tags"],
      ["Messages", "#messages"],
      ["Tabs", "#tabs"],
      ["Modal, dropdown, tooltip", "#overlays"],
    ],
  },
  {
    label: "Pages",
    icon: "login",
    items: [["Login page", "#login"]],
  },
];

function initial(name, allowed, fallback) {
  const value = new URLSearchParams(window.location.search).get(name);
  return allowed.includes(value) ? value : fallback;
}

export function App({ bulma }) {
  const [mode, setMode] = useState(() => initial("mode", ["light", "dark"], "light"));
  const [dir, setDir] = useState(() => initial("dir", ["ltr", "rtl"], "ltr"));
  const [hash, setHash] = useState(window.location.hash || "#dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const dark = mode === "dark";
  const rtl = dir === "rtl";

  useEffect(() => {
    document.body.className = dark ? "dark-mode" : "default-mode";
    document.documentElement.setAttribute("dir", dir);
    document.querySelector('meta[name="color-scheme"]').setAttribute("content", dark ? "dark" : "light");
    document.getElementById("bulma-css").setAttribute("href", rtl ? bulma.rtl : bulma.ltr);
    document.getElementById("lumen-css").setAttribute("href", `./lumen${dark ? "-dark" : ""}${rtl ? "-rtl" : ""}.css`);
  }, [dark, dir, rtl, bulma]);

  useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    // The real command palette, loaded like the panel loads it (deferred script after the page).
    if (!document.getElementById("lumen-island-script")) {
      const script = document.createElement("script");
      script.id = "lumen-island-script";
      script.defer = true;
      script.src = "./lumen-island.js";
      document.body.appendChild(script);
    }
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const clock = useMemo(() => new Date().toISOString().slice(11, 16), []);

  return (
    <>
      <header id="header">
        <nav id="top-nav" aria-label="Gallery">
          <div className="level is-mobile">
            <div className="level-left">
              <a className="level-item" href="#dashboard">
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
                Lumen design-system gallery | <span className="has-margin-left-xsmall">{clock}</span>
              </div>
            </div>
            <div className="level-right">
              <button
                className="button level-item"
                type="button"
                aria-pressed={dark}
                onClick={() => setMode(dark ? "light" : "dark")}
              >
                <span className="icon is-medium">
                  <Svg name={dark ? "sun" : "moon"} />
                </span>
                <span>{dark ? "Light mode" : "Dark mode"}</span>
              </button>
              <button className="button level-item" type="button" aria-pressed={rtl} onClick={() => setDir(rtl ? "ltr" : "rtl")}>
                <span className="icon is-medium">
                  <Svg name="direction" />
                </span>
                <span>{rtl ? "Left to right" : "Right to left"}</span>
              </button>
              <a className="level-item" href="#tokens" aria-label="Account (example)">
                <span className="icon is-large">
                  <span className="fa-stack fa-1x">
                    <Svg name="square" className="fa fa-square fa-stack-2x" />
                    <Svg name="user" className="fa fa-user fa-stack-1x fa-inverse" />
                  </span>
                </span>
              </a>
              <button
                id="app-sidebar-toggle"
                className="button level-item is-hidden-desktop"
                type="button"
                aria-expanded={sidebarOpen}
                aria-controls="sidebar"
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                <span className="icon is-medium">
                  <Svg name="bars" />
                </span>
                <span className="is-sr-only">Menu</span>
              </button>
            </div>
          </div>
        </nav>
      </header>

      <section id="sidebar" className={sidebarOpen ? "is-active" : undefined} aria-label="Sections">
        <nav id="sidebar-navigation" className="menu has-margin-x-xsmall">
          {NAV.map((group) => (
            <div className="app-menu-group has-margin-bottom-medium" key={group.label}>
              <p className="menu-label has-margin-bottom-small">
                <Icon name={group.icon} />
                {group.label}
              </p>
              <ul className="menu-list">
                {group.items.map(([label, href]) => (
                  <li key={href}>
                    <a href={href} className={hash === href ? "is-active" : undefined} onClick={() => setSidebarOpen(false)}>
                      {label}
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
        <main id="content">
          <nav className="breadcrumb is-small has-margin-bottom-none" aria-label="breadcrumbs">
            <ul>
              <li>
                <a href="#dashboard">Lumen</a>
              </li>
              <li className="is-active">
                <a href="#dashboard" aria-current="page">
                  Gallery
                </a>
              </li>
            </ul>
          </nav>
          <div className="content-title">
            <h1 className="title is-4">Lumen design-system gallery</h1>
          </div>
          <article className="message is-info">
            <div className="message-body">
              Press <kbd>Ctrl</kbd> + <kbd>K</kbd> (<kbd>⌘</kbd> <kbd>K</kbd> on a Mac) to open the command palette. It
              reads this sidebar, exactly as it reads the panel's own navigation.
            </div>
          </article>
          <Dashboard />
          <Tokens mode={mode} />
          <Tables />
          <Forms />
          <Buttons />
          <Tags />
          <Messages />
          <Tabs />
          <Overlays />
          <Login dark={dark} />
        </main>
        <footer id="footer">
          <div className="content has-text-centered">
            <p>
              lumen-panel, a Luminare Development open-source project. Not affiliated with or endorsed by Keyweb AG.
              KeyHelp is a registered trademark of Keyweb AG.
            </p>
          </div>
        </footer>
      </section>
    </>
  );
}
