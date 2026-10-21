// Fuzzy matching for the command palette. Plain JavaScript, no dependencies, no DOM.
//
// A query matches a text when its characters appear in order (a subsequence). The score prefers
// matches at the start of the text and of words, and runs of consecutive characters; gaps and
// long texts cost a little. Accents and case are ignored: "domanen" finds "Domänen".

/** Lower case without diacritics, so "Ü" matches "u". Keeps one character per input character. */
export function fold(text) {
  let out = "";
  for (const ch of String(text)) {
    const base = ch.normalize("NFD").replace(/\p{M}+/gu, "");
    out += (base.length === 1 ? base : ch).toLowerCase();
  }
  return out;
}

const WORD_START = /[\s\-_/.,:;()[\]|]/u;

/**
 * Score one query token against one text. Returns null if it does not match, otherwise
 * { score, indices } where indices are the matched character positions in `text`.
 */
export function scoreToken(token, text) {
  const q = fold(token);
  const t = fold(text);
  if (!q) return { score: 0, indices: [] };
  const chars = Array.from(t);
  const indices = [];
  let score = 0;
  let qi = 0;
  let prev = -2;
  const qChars = Array.from(q);
  for (let i = 0; i < chars.length && qi < qChars.length; i += 1) {
    if (chars[i] !== qChars[qi]) continue;
    let s = 1;
    if (i === 0) s += 8;
    else if (WORD_START.test(chars[i - 1])) s += 6;
    if (i === prev + 1) s += 4;
    else if (prev >= 0) s -= Math.min(3, (i - prev - 1) * 0.25);
    score += s;
    indices.push(i);
    prev = i;
    qi += 1;
  }
  if (qi < qChars.length) return null;
  // A plain substring beats a scattered match; shorter texts win ties.
  if (t.includes(q)) score += 5;
  score -= chars.length * 0.02;
  return { score, indices };
}

/**
 * Rank entries ({ label, group, ... }) for a query. Every whitespace-separated token must match
 * the label or the group; label matches count fully, group matches half. Without a query the
 * entries keep their order (the panel's own menu order).
 */
export function search(entries, query, limit = 50) {
  const tokens = String(query).trim().split(/\s+/u).filter(Boolean);
  if (tokens.length === 0) {
    return entries.slice(0, limit).map((entry) => ({ entry, score: 0, indices: [] }));
  }
  const results = [];
  for (const entry of entries) {
    let total = 0;
    const indices = new Set();
    let ok = true;
    for (const token of tokens) {
      const inLabel = scoreToken(token, entry.label);
      const inGroup = entry.group ? scoreToken(token, entry.group) : null;
      if (!inLabel && !inGroup) {
        ok = false;
        break;
      }
      if (inLabel && (!inGroup || inLabel.score >= inGroup.score / 2)) {
        total += inLabel.score;
        for (const i of inLabel.indices) indices.add(i);
      } else {
        total += inGroup.score / 2;
      }
    }
    if (ok) results.push({ entry, score: total, indices: [...indices].sort((a, b) => a - b) });
  }
  results.sort((a, b) => b.score - a.score || a.entry.label.length - b.entry.label.length);
  return results.slice(0, limit);
}

/** Split a label into [{ text, hit }] parts for highlighting the matched characters. */
export function highlight(label, indices) {
  const chars = Array.from(label);
  const hits = new Set(indices);
  const parts = [];
  for (let i = 0; i < chars.length; i += 1) {
    const hit = hits.has(i);
    const last = parts[parts.length - 1];
    if (last && last.hit === hit) last.text += chars[i];
    else parts.push({ text: chars[i], hit });
  }
  return parts;
}
