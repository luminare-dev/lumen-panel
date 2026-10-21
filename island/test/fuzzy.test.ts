import { describe, expect, it } from "vitest";
import { fold, highlight, scoreToken, search } from "../src/fuzzy";

const entries = [
  { id: "1", label: "Domains", group: "Domains & SSL" },
  { id: "2", label: "SSL certificates", group: "Domains & SSL" },
  { id: "3", label: "Email accounts", group: "Email" },
  { id: "4", label: "Database status", group: "Server" },
  { id: "5", label: "Domänen", group: "Domains & SSL" },
  { id: "6", label: "DNS editor", group: "Domains & SSL" },
];

describe("fold", () => {
  it("removes accents and case but keeps one character per character", () => {
    expect(fold("Domänen")).toBe("domanen");
    expect(fold("ÜBER")).toBe("uber");
    expect(Array.from(fold("Ångström"))).toHaveLength(Array.from("Ångström").length);
  });
});

describe("scoreToken", () => {
  it("matches a subsequence and nothing else", () => {
    expect(scoreToken("dmn", "Domains")).not.toBeNull();
    expect(scoreToken("xyz", "Domains")).toBeNull();
    expect(scoreToken("dom", "Domains")?.indices).toEqual([0, 1, 2]);
    expect(scoreToken("", "Domains")).toEqual({ score: 0, indices: [] });
  });

  it("prefers prefixes and word starts over scattered matches", () => {
    const prefix = scoreToken("ssl", "SSL certificates")!.score;
    const scattered = scoreToken("ssl", "Database status list")!.score;
    expect(prefix).toBeGreaterThan(scattered);
    const wordStart = scoreToken("cert", "SSL certificates")!.score;
    const inside = scoreToken("cert", "Concerts")!.score;
    expect(wordStart).toBeGreaterThan(inside);
  });
});

describe("search", () => {
  it("ranks the best label first and ignores accents", () => {
    expect(search(entries, "ssl")[0]?.entry.label).toBe("SSL certificates");
    expect(search(entries, "domanen")[0]?.entry.label).toBe("Domänen");
    expect(search(entries, "mail")[0]?.entry.label).toBe("Email accounts");
  });

  it("needs every token to match the label or the group", () => {
    expect(search(entries, "dns")[0]?.entry.label).toBe("DNS editor");
    const both = search(entries, "domains dns").map((r) => r.entry.label);
    expect(both).toContain("DNS editor");
    expect(both).not.toContain("Email accounts");
    expect(search(entries, "server status").map((r) => r.entry.label)).toEqual(["Database status"]);
    expect(search(entries, "nothing here")).toEqual([]);
  });

  it("keeps the menu order and the limit for an empty query", () => {
    expect(search(entries, "   ").map((r) => r.entry.id)).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect(search(entries, "", 2)).toHaveLength(2);
  });
});

describe("highlight", () => {
  it("groups matched and unmatched characters", () => {
    expect(highlight("Domains", [0, 1, 2])).toEqual([
      { text: "Dom", hit: true },
      { text: "ains", hit: false },
    ]);
    expect(highlight("ab", [])).toEqual([{ text: "ab", hit: false }]);
  });
});
