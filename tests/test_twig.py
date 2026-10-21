"""Tests for the Twig sanity check and the asset reference scan used by verify."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))

from lumen_panel.twig import asset_references, check, tokenize  # noqa: E402


class TwigCheckTest(unittest.TestCase):
    def test_balanced_templates_pass(self):
        ok = [
            "{% extends 'a.twig' %}{% block x %}{% if a %}1{% elseif b %}2{% else %}3{% endif %}{% endblock %}",
            "{% for i in items %}{{ i }}{% else %}none{% endfor %}",
            "{% set x = {'a': {'b': '%}'}} %}{{ x|json_encode }}",
            "{% set body %}text{% endset %}",
            "{% block title page_title %}",
            "{# {% if comment %} is ignored #}",
            "{% verbatim %}{% if raw %}{{ not parsed{% endverbatim %}",
            "{% embed 'card.twig' with {'a': 1} %}{% block content %}x{% endblock %}{% endembed %}",
            "{% macro m(p) %}{{ p }}{% endmacro %}",
            "<script>var o = {a: 1};</script>",
        ]
        for src in ok:
            self.assertEqual(check(src), [], src)

    def test_problems_are_reported(self):
        cases = {
            "{% if a %}x": "if is never closed",
            "{% endif %}": "endif without if",
            "{% block a %}{% if b %}{% endblock %}": "endblock closes if",
            "{{ a ": "never closed",
            "{# a ": "comment is never closed",
            "{% else %}": "else outside",
            "{{ 'unclosed }}": "unclosed string",
        }
        for src, expected in cases.items():
            problems = "\n".join(check(src))
            self.assertIn(expected, problems, src)

    def test_tokenize_keeps_line_numbers(self):
        toks = tokenize("a\n{{ b }}\n\n{% c %}")
        self.assertEqual([(t.kind, t.line) for t in toks], [("var", 2), ("tag", 4)])


class AssetReferenceTest(unittest.TestCase):
    def test_ternaries_expand(self):
        src = ('<link href="/theme/lumen/assets/lumen{{ dark ? \'-dark\' }}{{ dir == \'rtl\' ? \'-rtl\' }}.css?v=1">'
               '<img src="/theme/lumen/assets/brand/logo-{{ dark ? \'dark\' : \'light\' }}.svg?v=1">'
               '<script src="/theme/lumen/assets/lumen-island.js?v=x"></script>'
               '<img src="theme/bulma/assets/img/keyhelp.svg">')
        self.assertEqual(asset_references(src), [
            "assets/brand/logo-dark.svg", "assets/brand/logo-light.svg", "assets/lumen-dark-rtl.css",
            "assets/lumen-dark.css", "assets/lumen-island.js", "assets/lumen-rtl.css", "assets/lumen.css",
        ])

    def test_the_theme_folder_is_matched_exactly(self):
        src = ('<link href="/theme/lumen-dark/assets/lumen-night{{ dir == \'rtl\' ? \'-rtl\' }}.css?v=1">'
               '<script src="/theme/lumen/assets/lumen-island.js?v=x"></script>')
        self.assertEqual(asset_references(src, "lumen-dark"), ["assets/lumen-night-rtl.css", "assets/lumen-night.css"])
        self.assertEqual(asset_references(src, "lumen"), ["assets/lumen-island.js"],
                         "theme/lumen/ never matches theme/lumen-dark/")
        self.assertEqual(asset_references(src), ["assets/lumen-island.js"])

    def test_unknown_expressions_are_flagged(self):
        refs = asset_references('<img src="/theme/lumen/assets/{{ file }}">')
        self.assertTrue(refs and refs[0].startswith("<dynamic>"), refs)


if __name__ == "__main__":
    unittest.main()
