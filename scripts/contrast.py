#!/usr/bin/env python3
"""Contrast table for the Lumen design tokens (Python standard library only).

Reads src/styles/tokens.css (the light :root block and the dark-mode block) and
src/styles/contrast-pairs.json, then:
  * recomputes every derived colour written as "mix(a NN%, b)" and checks its hex;
  * computes the WCAG 2.x contrast ratio of every pair in each of its modes: light (Lumen),
    dark (Lumen in the panel's dark mode) and night (Lumen Dark, which uses the dark token set
    on top of the panel's light stylesheet). A pair applies to all three unless it lists its
    "modes"; a pair Lumen Dark alone uses (the editors, the inverted chart labels) lists
    ["night"]. A colour may be a token name or a literal "#RRGGBB" the stylesheet produces;
  * writes docs/contrast.md (or, with --check, fails when that file is out of date);
  * exits 1 when a pair is below its minimum (4.5:1 text, 3:1 UI parts) or a mix is wrong.

Optional: --kit PATH compares the brand colours with the kit's palette/tokens.json.

Usage: python3 scripts/contrast.py [--check] [--kit /path/to/brand]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "src" / "styles" / "tokens.css"
PAIRS = ROOT / "src" / "styles" / "contrast-pairs.json"
DOC = ROOT / "docs" / "contrast.md"

DECL_RE = re.compile(r"--lm-([a-z0-9-]+)\s*:\s*([^;]+);(?:[ \t]*/\*\s*(.*?)\s*\*/)?")
MIX_RE = re.compile(r"^mix\(([a-z0-9-]+)\s+(\d+)%,\s*([a-z0-9-]+)\)$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
VAR_RE = re.compile(r"^var\(--lm-([a-z0-9-]+)\)$")
DARK_SELECTOR = ":root:has(> body.dark-mode),\nbody.dark-mode {"


def blocks(css: str) -> tuple[str, str]:
    light_start = css.index(":root {")
    dark_start = css.index(DARK_SELECTOR)
    light = css[light_start:css.index("}", light_start)]
    dark = css[dark_start + len(DARK_SELECTOR):css.index("}", dark_start + len(DARK_SELECTOR))]
    return light, dark


def declarations(block: str) -> dict[str, tuple[str, str | None]]:
    return {m.group(1): (m.group(2).strip(), m.group(3)) for m in DECL_RE.finditer(block)}


MODES = ("light", "dark", "night")


def resolve(name: str, decls: dict[str, tuple[str, str | None]], seen: tuple[str, ...] = ()) -> str | None:
    if HEX_RE.match(name):
        return name.upper()
    if name in seen or name not in decls:
        return None
    value = decls[name][0]
    if HEX_RE.match(value):
        return value.upper()
    m = VAR_RE.match(value)
    return resolve(m.group(1), decls, seen + (name,)) if m else None


def _channel(c: int) -> float:
    v = c / 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, share: float) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{round(int(a[i:i + 2], 16) * share + int(b[i:i + 2], 16) * (1 - share)):02X}"
                         for i in (0, 2, 4))


def mode_declarations(css: str) -> dict[str, dict[str, tuple[str, str | None]]]:
    """The token values of each mode. Lumen Dark (night) puts the dark block on :root."""
    light_block, dark_block = blocks(css)
    light = declarations(light_block)
    dark = {**light, **declarations(dark_block)}
    return {"light": light, "dark": dark, "night": dark}


def pair_modes(pair: dict) -> tuple[str, ...]:
    return tuple(m for m in MODES if m in pair.get("modes", MODES))


def analyse(css: str, pairs: list[dict]) -> tuple[list[dict], list[str]]:
    modes = mode_declarations(css)
    light, dark = modes["light"], modes["dark"]
    problems: list[str] = []
    for mode, decls in (("light", light), ("dark", dark)):
        for name, (value, comment) in decls.items():
            if not comment or not comment.startswith("mix("):
                continue
            m = MIX_RE.match(comment)
            if not m:
                problems.append(f"{mode} --lm-{name}: cannot read {comment!r}")
                continue
            a, b = resolve(m.group(1), decls), resolve(m.group(3), decls)
            if not a or not b:
                problems.append(f"{mode} --lm-{name}: unknown colour in {comment!r}")
                continue
            want = mix(a, b, int(m.group(2)) / 100)
            if value.upper() != want:
                problems.append(f"{mode} --lm-{name}: {value} is not {comment} = {want}")
    rows: list[dict] = []
    for pair in pairs:
        row: dict = {"pair": pair, **{m: None for m in MODES}}
        unknown = set(pair.get("modes", MODES)) - set(MODES)
        if unknown or not pair_modes(pair):
            problems.append(f"{name(pair['fg'])} on {name(pair['bg'])}: modes must be some of {', '.join(MODES)}")
        for mode in pair_modes(pair):
            decls = modes[mode]
            fg, bg = resolve(pair["fg"], decls), resolve(pair["bg"], decls)
            if not fg or not bg:
                problems.append(f"{mode}: cannot resolve {name(pair['fg'])} or {name(pair['bg'])}")
                continue
            r = ratio(fg, bg)
            row[mode] = (r, fg, bg)
            if r < pair["min"]:
                problems.append(f"{mode}: {name(pair['fg'])} on {name(pair['bg'])} is {r:.2f}:1, "
                                f"needs {pair['min']}:1 ({pair['use']})")
        rows.append(row)
    return rows, problems


def name(colour: str) -> str:
    """How a pair's colour is written: --lm-<token>, or the literal hex."""
    return colour if HEX_RE.match(colour) else f"--lm-{colour}"


def cell(row: dict, mode: str) -> str:
    if row[mode] is None:
        return "n/a"
    r, fg, bg = row[mode]
    mark = "pass" if r >= row["pair"]["min"] else "**FAIL**"
    return f"{int(r * 100) / 100:.2f} {mark} (`{fg}` on `{bg}`)"


def render(rows: list[dict]) -> str:
    out = [
        "# Contrast",
        "",
        "Generated by `python3 scripts/contrast.py` from `src/styles/tokens.css` and",
        "`src/styles/contrast-pairs.json`. Text needs 4.5:1, UI parts 3:1 (WCAG 2.2 AA).",
        "",
        "| Foreground | Background | Used for | Min | Light | Dark and Lumen Dark |",
        "|---|---|---|---|---|---|",
    ]
    night_only = [row for row in rows if pair_modes(row["pair"]) == ("night",)]
    shared = [row for row in rows if row not in night_only]
    for row in shared:
        p = row["pair"]
        dark = cell(row, "dark")
        if row["night"] is not None and row["dark"] is not None and row["night"] != row["dark"]:
            dark += f"; Lumen Dark {cell(row, 'night')}"
        out.append(f"| `{name(p['fg'])}` | `{name(p['bg'])}` | {p['use']} | {p['min']} | {cell(row, 'light')} | {dark} |")
    if night_only:
        out += [
            "",
            "## Lumen Dark only",
            "",
            "| Foreground | Background | Used for | Min | Lumen Dark |",
            "|---|---|---|---|---|",
        ]
        for row in night_only:
            p = row["pair"]
            out.append(f"| `{name(p['fg'])}` | `{name(p['bg'])}` | {p['use']} | {p['min']} | {cell(row, 'night')} |")
    out.append("")
    return "\n".join(out)


def kit_problems(css: str, kit: Path) -> list[str]:
    data = json.loads((kit / "palette" / "tokens.json").read_text(encoding="utf-8"))
    light = declarations(blocks(css)[0])
    problems = []
    for key, info in data["colors"].items():
        for name, hex_value in ((key, info["hex"]), (f"{key}-bright", info.get("bright"))):
            if hex_value and name in light and light[name][0].upper() != hex_value.upper():
                problems.append(f"--lm-{name} is {light[name][0]}, the brand kit says {hex_value}")
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("--check", action="store_true", help="do not write docs/contrast.md; fail if it is stale")
    p.add_argument("--kit", type=Path, help="brand kit folder to compare the brand colours with")
    args = p.parse_args(argv)
    css = TOKENS.read_text(encoding="utf-8")
    pairs = json.loads(PAIRS.read_text(encoding="utf-8"))["pairs"]
    rows, problems = analyse(css, pairs)
    if args.kit:
        problems += kit_problems(css, args.kit)
    text = render(rows)
    if args.check:
        if not DOC.is_file() or DOC.read_text(encoding="utf-8") != text:
            problems.append("docs/contrast.md is out of date: run python3 scripts/contrast.py")
    else:
        DOC.write_text(text, encoding="utf-8")
    for prob in problems:
        print(f"error: {prob}")
    lowest = min((row[m][0] for row in rows for m in MODES if row[m]), default=0)
    checks = sum(1 for row in rows for m in MODES if row[m])
    print(f"{len(rows)} pairs, {checks} checks in light, dark and Lumen Dark, lowest ratio "
          f"{int(lowest * 100) / 100:.2f}:1, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
