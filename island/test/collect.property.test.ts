// Property-based tests of the palette's link filter (fast-check): safeHref offers only absolute
// http(s) URLs, and never a script, data or file link, also in mixed case, after spaces or control
// characters, or with a tab or line break inside the scheme (the URL parser drops those).
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { safeHref } from "../src/collect";

const RUNS = { numRuns: 300 };
const BASE = "https://panel.example.org/index.php";

// Spaces and C0 control characters: the URL parser removes them in front of a URL.
const lead = fc.string({ unit: fc.constantFrom(" ", "\t", "\n", "\r", "\u0000", "\u001f"), maxLength: 3 });
// The same, plus whitespace the URL parser keeps (no-break space, byte order mark, line separator).
const anyLead = fc.string({
  unit: fc.constantFrom(" ", "\t", "\n", "\r", "\u0000", "\u001f", " ", "﻿", " "),
  maxLength: 3,
});
const blocked = fc.mixedCase(fc.constantFrom("javascript", "java\tscript", "java\nscript", "data", "vbscript", "file"));
const other = fc.mixedCase(fc.constantFrom("http", "https", "ftp", "mailto", "blob"));
const separator = fc.constantFrom(":", "://", ":alert(1)//");
const blockedLink = fc.tuple(lead, blocked, separator, fc.string()).map((parts) => parts.join(""));
const anyHref = fc.oneof(
  blockedLink,
  fc.tuple(anyLead, fc.oneof(blocked, other), separator, fc.string()).map((parts) => parts.join("")),
  fc.webUrl({ withQueryParameters: true, withFragments: true }),
  fc.string({ unit: "binary" }),
);

describe("safeHref (properties)", () => {
  it("returns an absolute http(s) URL or null, for any href", () => {
    fc.assert(
      fc.property(anyHref, (href) => {
        const url = safeHref(href, BASE);
        if (url !== null) expect(url).toMatch(/^https?:\/\//u);
      }),
      RUNS,
    );
  });

  it("never offers a javascript:, data:, vbscript: or file: link", () => {
    fc.assert(
      fc.property(blockedLink, (href) => {
        expect(safeHref(href, BASE)).toBeNull();
      }),
      RUNS,
    );
  });
});
