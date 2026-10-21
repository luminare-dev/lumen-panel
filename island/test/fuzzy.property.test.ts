// Property-based tests of the palette's fuzzy search (fast-check): random labels, groups and
// queries, checked against what island/src/fuzzy.ts promises. A failing property prints the seed
// and the shrunk counterexample; pass them to fc.assert(..., { seed, path }) to replay it.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { fold, highlight, scoreToken, search } from "../src/fuzzy";

const RUNS = { numRuns: 300 };

// Letters in both cases, ä Ä é, sharp s, dotted capital I, dotless i, a lone combining acute
// accent, an emoji (two UTF-16 units), word separators and a digit.
const CHARS = ["a", "A", "b", "B", "d", "D", "s", "S", "ä", "Ä", "é", "E", "ß", "İ",
  "ı", "́", "\u{1f600}", "-", "/", "&", "1"];
const text = fc.string({ unit: fc.constantFrom(...CHARS, " "), maxLength: 16 });
const word = fc.string({ unit: fc.constantFrom(...CHARS), minLength: 1, maxLength: 4 }); // one query token
const ascii = fc.string({ unit: "grapheme-ascii" });
const anyText = fc.string({ unit: "binary" }); // any code point
const anyUtf16 = fc.string({ unit: fc.nat(0xffff).map((c) => String.fromCharCode(c)) }); // lone surrogates too
const space = fc.constantFrom(" ", "  ", "\t", "\n", " ", "　");
const entry = fc.record({ label: text, group: text });
// The tokens, and a query that joins them with whitespace and pads it with whitespace.
const query = fc
  .tuple(fc.array(word, { maxLength: 3 }), space, space)
  .map(([tokens, gap, pad]) => ({ tokens, query: pad + tokens.join(gap) + pad }));

const codePoints = (s: string): string[] => Array.from(s);

function isSubsequence(needle: readonly string[], hay: readonly string[]): boolean {
  let i = 0;
  for (const ch of hay) if (i < needle.length && ch === needle[i]) i += 1;
  return i === needle.length;
}

describe("fold (properties)", () => {
  it("keeps one code point per code point and is idempotent, for any string", () => {
    fc.assert(
      fc.property(fc.oneof(text, anyText, anyUtf16), (s) => {
        const folded = fold(s);
        expect(codePoints(folded)).toHaveLength(codePoints(s).length);
        expect(fold(folded)).toBe(folded);
      }),
      RUNS,
    );
  });
});

describe("scoreToken (properties)", () => {
  it("matches exactly when the folded token is a subsequence of the folded text", () => {
    fc.assert(
      fc.property(word, text, (token, label) => {
        const q = codePoints(fold(token));
        const t = codePoints(fold(label));
        const result = scoreToken(token, label);
        expect(result !== null).toBe(isSubsequence(q, t));
        if (result === null) return;
        expect(Number.isFinite(result.score)).toBe(true);
        expect(result.indices).toHaveLength(q.length);
        result.indices.forEach((i, k) => {
          expect(t[i]).toBe(q[k]);
          if (k > 0) expect(i).toBeGreaterThan(result.indices[k - 1]!);
        });
      }),
      RUNS,
    );
  });

  it("finds a text from any subsequence of its characters", () => {
    const picked = text.chain((label) => fc.tuple(fc.constant(label), fc.subarray(codePoints(label))));
    fc.assert(
      fc.property(picked, ([label, chars]) => {
        expect(scoreToken(chars.join(""), label)).not.toBeNull();
      }),
      RUNS,
    );
  });

  it("ignores case and accents: only the folded forms count", () => {
    fc.assert(
      fc.property(word, text, (token, label) => {
        expect(scoreToken(token, label)).toEqual(scoreToken(fold(token), fold(label)));
      }),
      RUNS,
    );
    fc.assert(
      fc.property(ascii, ascii, (token, label) => {
        expect(scoreToken(token.toUpperCase(), label.toLowerCase())).toEqual(scoreToken(token, label));
      }),
      RUNS,
    );
  });
});

describe("search (properties)", () => {
  it("returns exactly the entries every token finds, best first, and the limit only cuts the list", () => {
    fc.assert(
      fc.property(fc.array(entry, { maxLength: 8 }), query, fc.nat(10), (entries, { tokens, query: q }, limit) => {
        const finds = (token: string, e: { label: string; group: string }) =>
          scoreToken(token, e.label) !== null || (e.group !== "" && scoreToken(token, e.group) !== null);
        const expected = entries.filter((e) => tokens.every((token) => finds(token, e)));
        const results = search(entries, q, limit);
        expect(results).toHaveLength(Math.min(limit, expected.length));
        for (const r of results) expect(expected).toContain(r.entry);
        expect(results).toEqual(search(entries, q, entries.length).slice(0, limit));
        if (tokens.length === 0) {
          // Without a query the entries keep their order.
          expect(results.map((r) => r.entry)).toEqual(entries.slice(0, limit));
          return;
        }
        for (let k = 1; k < results.length; k += 1) {
          const a = results[k - 1]!;
          const b = results[k]!;
          expect(a.score > b.score || (a.score === b.score && a.entry.label.length <= b.entry.label.length)).toBe(true);
        }
      }),
      RUNS,
    );
  });

  it("highlights only label characters, and the highlights of one token spell it", () => {
    fc.assert(
      fc.property(fc.array(entry, { maxLength: 8 }), word, (entries, token) => {
        for (const r of search(entries, token)) {
          const length = codePoints(r.entry.label).length;
          r.indices.forEach((i, k) => {
            expect(i).toBeGreaterThanOrEqual(0);
            expect(i).toBeLessThan(length);
            if (k > 0) expect(i).toBeGreaterThan(r.indices[k - 1]!);
          });
          if (r.indices.length === 0) continue; // found through the group
          const spelled = highlight(r.entry.label, r.indices)
            .filter((part) => part.hit)
            .flatMap((part) => codePoints(part.text).map((ch) => fold(ch)))
            .join("");
          expect(spelled).toBe(fold(token));
        }
      }),
      RUNS,
    );
  });
});

describe("highlight (properties)", () => {
  it("splits any label losslessly into alternating parts, whatever the indices", () => {
    fc.assert(
      fc.property(fc.oneof(text, anyText), fc.array(fc.integer({ min: -3, max: 40 })), (label, indices) => {
        const parts = highlight(label, indices);
        expect(parts.map((p) => p.text).join("")).toBe(label);
        parts.forEach((p, k) => {
          expect(p.text).not.toBe("");
          if (k > 0) expect(p.hit).not.toBe(parts[k - 1]!.hit);
        });
        const length = codePoints(label).length;
        const highlighted = parts.filter((p) => p.hit).reduce((n, p) => n + codePoints(p.text).length, 0);
        expect(highlighted).toBe(new Set(indices.filter((i) => i >= 0 && i < length)).size);
      }),
      RUNS,
    );
  });
});
