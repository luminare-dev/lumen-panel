"""A small Twig syntax sanity check and the asset reference scan used by ``verify``.

This is not a Twig parser. It finds the ``{{ }}``, ``{% %}`` and ``{# #}`` delimiters the way
Twig's lexer does (quotes and brackets inside expressions are respected, ``verbatim`` sections are
skipped) and checks that every block tag is closed in the right order. That is enough to catch
a patch that breaks a template, which is what it is for.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

# Tags that open a body which must be closed with end<tag>.
PAIRED = {"block", "if", "for", "embed", "macro", "apply", "autoescape", "filter", "spaceless",
          "with", "sandbox", "cache", "guard", "set", "verbatim"}
# Middle tags and the openers they may appear in.
MIDDLE = {"else": {"if", "for"}, "elseif": {"if"}}

_OPEN_RE = re.compile(r"\{([{%#])")
_TAG_NAME_RE = re.compile(r"^\s*-?\s*~?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(.*?)\s*[-~]?\s*$", re.DOTALL)
_ENDVERBATIM_RE = re.compile(r"\{%-?\s*endverbatim\s*-?%\}")


@dataclass(frozen=True)
class Token:
    kind: str      # "var", "tag" or "comment"
    body: str      # text between the delimiters
    line: int


class TwigSyntaxError(Exception):
    pass


def _line(src: str, pos: int) -> int:
    return src.count("\n", 0, pos) + 1


def _scan_expression(src: str, start: int, closer: str) -> int:
    """Index of the closer that ends the expression starting at ``start`` (quotes and brackets aware)."""
    depth = 0
    i = start
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in "'\"":
            j = i + 1
            while j < n and src[j] != ch:
                j += 2 if src[j] == "\\" else 1
            if j >= n:
                raise TwigSyntaxError(f"line {_line(src, i)}: unclosed string")
            i = j + 1
            continue
        if depth == 0 and src.startswith(closer, i):
            return i
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        i += 1
    raise TwigSyntaxError(f"line {_line(src, start)}: '{{{closer[0]}' is never closed with '{closer}'")


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while True:
        m = _OPEN_RE.search(src, pos)
        if not m:
            return tokens
        kind = m.group(1)
        start = m.end()
        if kind == "#":
            end = src.find("#}", start)
            if end < 0:
                raise TwigSyntaxError(f"line {_line(src, m.start())}: comment is never closed with '#}}'")
            tokens.append(Token("comment", src[start:end], _line(src, m.start())))
            pos = end + 2
            continue
        closer = "}}" if kind == "{" else "%}"
        end = _scan_expression(src, start, closer)
        body = src[start:end]
        tok = Token("var" if kind == "{" else "tag", body, _line(src, m.start()))
        tokens.append(tok)
        pos = end + 2
        if tok.kind == "tag" and _tag_name(body)[0] == "verbatim":
            v = _ENDVERBATIM_RE.search(src, pos)
            if not v:
                raise TwigSyntaxError(f"line {tok.line}: verbatim is never closed")
            tokens.append(Token("tag", "endverbatim", _line(src, v.start())))
            pos = v.end()


def _tag_name(body: str) -> tuple[str, str]:
    m = _TAG_NAME_RE.match(body)
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def _opens_body(name: str, args: str) -> bool:
    if name == "set":
        return "=" not in args            # {% set x %}...{% endset %}
    if name == "block":
        return len(args.split(None, 1)) < 2  # {% block title page_title %} is the short form
    return name in PAIRED


def check(src: str) -> list[str]:
    """Problems found in one template (empty list: the delimiters and block tags are balanced)."""
    try:
        tokens = tokenize(src)
    except TwigSyntaxError as exc:
        return [str(exc)]
    problems: list[str] = []
    stack: list[tuple[str, int]] = []
    for tok in tokens:
        if tok.kind != "tag":
            continue
        name, args = _tag_name(tok.body)
        if not name:
            problems.append(f"line {tok.line}: empty tag")
            continue
        if name.startswith("end"):
            opener = name[3:]
            if not stack:
                problems.append(f"line {tok.line}: {name} without {opener}")
            elif stack[-1][0] != opener:
                problems.append(f"line {tok.line}: {name} closes {stack[-1][0]} from line {stack[-1][1]}")
                stack.pop()
            else:
                stack.pop()
        elif name in MIDDLE:
            if not stack or stack[-1][0] not in MIDDLE[name]:
                problems.append(f"line {tok.line}: {name} outside {' or '.join(sorted(MIDDLE[name]))}")
        elif _opens_body(name, args):
            stack.append((name, tok.line))
    for name, line in reversed(stack):
        problems.append(f"line {line}: {name} is never closed")
    return problems


# --------------------------------------------------------------------------------------------
# Asset references: "/theme/lumen/assets/lumen{{ cond ? '-dark' }}.css?v=..." expands to the
# file names a page can request. Only the two forms used by the patches are understood:
# {{ expr ? 'a' }} (a or nothing) and {{ expr ? 'a' : 'b' }}.
# --------------------------------------------------------------------------------------------
_REF_RE = re.compile(r"""/?theme/lumen/(?P<path>(?:[^"'\s?<>{]|\{\{.*?\}\})+)""")
_TERNARY_RE = re.compile(r"""\{\{\s*[^{}?]*?\?\s*'([^']*)'\s*(?::\s*'([^']*)'\s*)?\}\}""")


def asset_references(src: str) -> list[str]:
    """Every theme/lumen/... path a template refers to, with simple ternaries expanded."""
    refs: list[str] = []
    for m in _REF_RE.finditer(src):
        path = m.group("path")
        parts: list[list[str]] = []
        pos = 0
        for t in _TERNARY_RE.finditer(path):
            parts.append([path[pos:t.start()]])
            parts.append([t.group(1), t.group(2) or ""])
            pos = t.end()
        parts.append([path[pos:]])
        for combo in itertools.product(*parts):
            ref = "".join(combo)
            if "{{" in ref or "}}" in ref:
                refs.append("<dynamic>" + ref)
            else:
                refs.append(ref)
    return sorted(set(refs))
