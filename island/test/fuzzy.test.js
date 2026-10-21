import assert from "node:assert/strict";
import { test } from "node:test";
import { fold, highlight, scoreToken, search } from "../src/fuzzy.js";

const entries = [
  { id: "1", label: "Domains", group: "Domains & SSL" },
  { id: "2", label: "SSL certificates", group: "Domains & SSL" },
  { id: "3", label: "Email accounts", group: "Email" },
  { id: "4", label: "Database status", group: "Server" },
  { id: "5", label: "Domänen", group: "Domains & SSL" },
  { id: "6", label: "DNS editor", group: "Domains & SSL" },
];

test("fold removes accents and case but keeps one character per character", () => {
  assert.equal(fold("Domänen"), "domanen");
  assert.equal(fold("ÜBER"), "uber");
  assert.equal(Array.from(fold("Ångström")).length, Array.from("Ångström").length);
});

test("a subsequence matches, anything else does not", () => {
  assert.ok(scoreToken("dmn", "Domains"));
  assert.equal(scoreToken("xyz", "Domains"), null);
  assert.deepEqual(scoreToken("dom", "Domains").indices, [0, 1, 2]);
});

test("prefix and word starts beat scattered matches", () => {
  const prefix = scoreToken("ssl", "SSL certificates").score;
  const scattered = scoreToken("ssl", "Database status list").score;
  assert.ok(prefix > scattered, `${prefix} > ${scattered}`);
  const wordStart = scoreToken("cert", "SSL certificates").score;
  const inside = scoreToken("cert", "Concerts").score;
  assert.ok(wordStart > inside, `${wordStart} > ${inside}`);
});

test("search ranks the best label first and ignores accents", () => {
  assert.equal(search(entries, "ssl")[0].entry.label, "SSL certificates");
  assert.equal(search(entries, "domanen")[0].entry.label, "Domänen");
  assert.equal(search(entries, "mail")[0].entry.label, "Email accounts");
});

test("every token must match the label or the group", () => {
  assert.equal(search(entries, "dns")[0].entry.label, "DNS editor");
  const both = search(entries, "domains dns").map((r) => r.entry.label);
  assert.ok(both.includes("DNS editor"), both.join(", "));
  assert.ok(!both.includes("Email accounts"), both.join(", "));
  assert.deepEqual(search(entries, "server status").map((r) => r.entry.label), ["Database status"]);
  assert.deepEqual(search(entries, "nothing here"), []);
});

test("an empty query keeps the menu order and the limit", () => {
  const all = search(entries, "   ");
  assert.deepEqual(all.map((r) => r.entry.id), ["1", "2", "3", "4", "5", "6"]);
  assert.equal(search(entries, "", 2).length, 2);
});

test("highlight groups matched and unmatched characters", () => {
  assert.deepEqual(highlight("Domains", [0, 1, 2]), [
    { text: "Dom", hit: true },
    { text: "ains", hit: false },
  ]);
  assert.deepEqual(highlight("ab", []), [{ text: "ab", hit: false }]);
});
