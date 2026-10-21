// Fuzzy matching for the command palette. No dependencies, no DOM.
//
// A query matches a text when its characters appear in order (a subsequence). The score prefers
// matches at the start of the text and of words, and runs of consecutive characters; gaps and
// long texts cost a little. Accents and case are ignored: "domanen" finds "Domänen".

import type { Match, Searchable } from "./types";

/** Lower case without diacritics, so "Ü" matches "u". Keeps one character per input character. */
export function fold(text: string): string {
  let out = "";
  for (const ch of String(text)) {
    const base = ch.normalize("NFD").replace(/\p{M}+/gu, "");
    out += (base.length === 1 ? base : ch).toLowerCase();
  }
  return out;
}

const WORD_START = /[\s\-_/.,:;()[\]|&]/u;

export interface TokenScore {
  score: number;
  indices: number[];
}

/**
 * Score one query token against one text. Returns null if it does not match, otherwise the
 * score and the matched character positions in `text`.
 */
export function scoreToken(token: string, text: string): TokenScore | null {
  const q = Array.from(fold(token));
  const t = Array.from(fold(text));
  if (q.length === 0) return { score: 0, indices: [] };
  const indices: number[] = [];
  let score = 0;
  let qi = 0;
  let prev = -2;
  for (let i = 0; i < t.length && qi < q.length; i += 1) {
    if (t[i] !== q[qi]) continue;
    let s = 1;
    if (i === 0) s += 8;
    else if (WORD_START.test(t[i - 1] ?? "")) s += 6;
    if (i === prev + 1) s += 4;
    else if (prev >= 0) s -= Math.min(3, (i - prev - 1) * 0.25);
    score += s;
    indices.push(i);
    prev = i;
    qi += 1;
  }
  if (qi < q.length) return null;
  // A plain substring beats a scattered match; shorter texts win ties.
  if (t.join("").includes(q.join(""))) score += 5;
  score -= t.length * 0.02;
  return { score, indices };
}

/**
 * Rank entries for a query. Every whitespace-separated token must match the label or the group;
 * label matches count fully, group matches half. Without a query the entries keep their order
 * (the panel's own menu order).
 */
export function search<T extends Searchable>(entries: readonly T[], query: string, limit = 50): Match<T>[] {
  const tokens = String(query).trim().split(/\s+/u).filter(Boolean);
  if (tokens.length === 0) {
    return entries.slice(0, limit).map((entry) => ({ entry, score: 0, indices: [] }));
  }
  const results: Match<T>[] = [];
  for (const entry of entries) {
    let total = 0;
    const indices = new Set<number>();
    let ok = true;
    for (const token of tokens) {
      const inLabel = scoreToken(token, entry.label);
      const inGroup = entry.group ? scoreToken(token, entry.group) : null;
      if (inLabel && (!inGroup || inLabel.score >= inGroup.score / 2)) {
        total += inLabel.score;
        for (const i of inLabel.indices) indices.add(i);
      } else if (inGroup) {
        total += inGroup.score / 2;
      } else {
        ok = false;
        break;
      }
    }
    if (ok) results.push({ entry, score: total, indices: [...indices].sort((a, b) => a - b) });
  }
  results.sort((a, b) => b.score - a.score || a.entry.label.length - b.entry.label.length);
  return results.slice(0, limit);
}

export interface Part {
  text: string;
  hit: boolean;
}

/** Split a label into parts for highlighting the matched characters. */
export function highlight(label: string, indices: readonly number[]): Part[] {
  const hits = new Set(indices);
  const parts: Part[] = [];
  Array.from(label).forEach((ch, i) => {
    const hit = hits.has(i);
    const last = parts[parts.length - 1];
    if (last && last.hit === hit) last.text += ch;
    else parts.push({ text: ch, hit });
  });
  return parts;
}
