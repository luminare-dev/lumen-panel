import assert from "node:assert/strict";
import { test } from "node:test";
import { cleanText, collectEntries, safeHref } from "../src/collect.js";

// A minimal stand-in for the few DOM methods collect.js uses, so the test needs no browser.
function el(tag, { attrs = {}, classes = [], text = "", children = [] } = {}) {
  const node = {
    tag,
    attrs,
    textContent: text || children.map((c) => c.textContent).join(" "),
    classList: { contains: (c) => classes.includes(c) },
    children,
    getAttribute: (name) => (name in attrs ? attrs[name] : null),
    querySelector: (sel) => node.querySelectorAll(sel)[0] || null,
    querySelectorAll: (sel) => select(node, sel),
  };
  node.classes = classes;
  return node;
}

function descendants(node) {
  return node.children.flatMap((c) => [c, ...descendants(c)]);
}

// Supports exactly the selectors collect.js uses.
function select(node, sel) {
  const all = descendants(node);
  const has = (n, cls) => n.classes.includes(cls);
  const within = (id) => all.filter((n) => n.attrs.id === id).flatMap(descendants);
  switch (sel) {
    case "#sidebar-navigation .app-menu-group":
      return within("sidebar-navigation").filter((n) => has(n, "app-menu-group"));
    case ".menu-label":
      return all.filter((n) => has(n, "menu-label"));
    case ".menu-list a[href]":
      return all.filter((n) => has(n, "menu-list")).flatMap(descendants).filter((n) => n.tag === "a" && n.attrs.href !== undefined);
    case '#header a[href*="return_to_admin"]':
      return within("header").filter((n) => n.tag === "a" && String(n.attrs.href || "").includes("return_to_admin"));
    case "#user-menu a.dropdown-item[href]":
      return within("user-menu").filter((n) => n.tag === "a" && has(n, "dropdown-item") && n.attrs.href !== undefined);
    default:
      throw new Error(`unsupported selector ${sel}`);
  }
}

function page() {
  const link = (text, href, extra = {}) => el("a", { attrs: { href, ...extra.attrs }, classes: extra.classes || [], text });
  const group = (label, links) =>
    el("div", { classes: ["app-menu-group"], children: [el("p", { classes: ["menu-label"], text: `  ${label}\n ` }), el("ul", { classes: ["menu-list"], children: links })] });
  const body = el("body", {
    children: [
      el("header", { attrs: { id: "header" }, children: [link("Back to administrator", "?page=intern&action=return_to_admin")] }),
      el("div", {
        attrs: { id: "user-menu" },
        children: [link("Profile", "?page=profile", { classes: ["dropdown-item"] }), link("Log out", "?page=logout", { classes: ["dropdown-item"] })],
      }),
      el("nav", {
        attrs: { id: "sidebar-navigation" },
        children: [
          group("Domains", [
            link(" Domains ", "?page=domains", { classes: ["is-active"] }),
            link("SSL", "?page=ssl_certificates"),
            link("Script", "javascript:alert(1)"),
            link("Empty", "#"),
            link("Domains", "?page=domains"),
          ]),
          group("Links", [link("Docs", "https://docs.example.org/", { attrs: { target: "_blank" } })]),
        ],
      }),
    ],
  });
  return { baseURI: "https://panel.example.org/index.php?page=dashboard", querySelectorAll: body.querySelectorAll, querySelector: body.querySelector };
}

test("cleanText collapses whitespace", () => {
  assert.equal(cleanText({ textContent: "  a\n  b  " }), "a b");
  assert.equal(cleanText(null), "");
});

test("safeHref resolves relative links and refuses script URLs", () => {
  const base = "https://panel.example.org/index.php";
  assert.equal(safeHref("?page=domains", base), "https://panel.example.org/index.php?page=domains");
  assert.equal(safeHref("javascript:alert(1)", base), null);
  assert.equal(safeHref(" JavaScript:void(0)", base), null);
  assert.equal(safeHref("data:text/html,x", base), null);
  assert.equal(safeHref("#", base), null);
  assert.equal(safeHref("", base), null);
  assert.equal(safeHref("#anchor-forms", base), "https://panel.example.org/index.php#anchor-forms");
});

test("collectEntries reads groups, the current page, the account links and skips unsafe links", () => {
  const entries = collectEntries(page(), { account: "Account" });
  const rows = entries.map((e) => [e.group, e.label, e.current, e.newTab]);
  assert.deepEqual(rows, [
    ["Domains", "Domains", true, false],
    ["Domains", "SSL", false, false],
    ["Links", "Docs", false, true],
    ["Account", "Back to administrator", false, false],
    ["Account", "Profile", false, false],
    ["Account", "Log out", false, false],
  ]);
  assert.equal(entries[0].href, "https://panel.example.org/index.php?page=domains");
  assert.equal(new Set(entries.map((e) => e.id)).size, entries.length);
});
