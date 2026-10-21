import { beforeEach, describe, expect, it } from "vitest";
import { cleanText, collectEntries, isInternalLayout, safeHref } from "../src/collect";
import { INTERNAL_PAGE, LOGIN_PAGE } from "./markup";

describe("cleanText", () => {
  it("collapses whitespace", () => {
    const p = document.createElement("p");
    p.textContent = "  a\n  b  ";
    expect(cleanText(p)).toBe("a b");
    expect(cleanText(null)).toBe("");
  });
});

describe("safeHref", () => {
  const base = "https://panel.example.org/index.php";
  it("resolves relative links", () => {
    expect(safeHref("?page=domains", base)).toBe("https://panel.example.org/index.php?page=domains");
    expect(safeHref("#anchor-forms", base)).toBe("https://panel.example.org/index.php#anchor-forms");
  });
  it("refuses empty links, '#' and script or data URLs", () => {
    for (const href of ["javascript:alert(1)", " JavaScript:void(0)", "data:text/html,x", "vbscript:x", "#", "", null]) {
      expect(safeHref(href, base)).toBeNull();
    }
    expect(safeHref("ftp://example.org/", base)).toBeNull();
  });
});

describe("collectEntries", () => {
  beforeEach(() => {
    document.body.innerHTML = INTERNAL_PAGE;
  });

  it("reads groups, the current page and the account links, and skips unsafe links", () => {
    const entries = collectEntries(document, { account: "Account" });
    expect(entries.map((e) => [e.group, e.label, e.current, e.newTab])).toEqual([
      ["Domains", "Domains", true, false],
      ["Domains", "SSL certificates", false, false],
      ["Email", "Email accounts", false, false],
      ["Email", "Documentation", false, true],
      ["Account", "Back to administrator", false, false],
      ["Account", "Profile", false, false],
      ["Account", "Log out", false, false],
    ]);
    expect(entries[1]?.href).toBe(new URL("?page=ssl_certificates", document.baseURI).href);
    expect(new Set(entries.map((e) => e.id)).size).toBe(entries.length);
  });

  it("detects the internal layout and nothing else", () => {
    expect(isInternalLayout(document)).toBe(true);
    document.body.innerHTML = LOGIN_PAGE;
    expect(isInternalLayout(document)).toBe(false);
    expect(collectEntries(document)).toEqual([]);
  });
});
