"""A small fake KeyHelp install for the generator tests, written for this project.

The templates are minimal Twig skeletons of our own. The only lines they share with the real
default theme are the patch anchors, which are read from patches/*.json, so the fixture always
matches the patch set under test.
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCHES = ROOT / "patches"


def anchors(patches_dir: Path = PATCHES) -> dict[str, tuple[str, str]]:
    """patch id -> (file, anchor)"""
    out = {}
    for path in sorted(patches_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("patches", [data]):
            out[item["id"]] = (item["file"], item["anchor"])
    return out


def _templates(a: dict[str, tuple[str, str]]) -> dict[str, str]:
    A = {k: v[1] for k, v in a.items()}
    files = {
        "layout/base.twig": (
            "<!DOCTYPE html>\n<html lang=\"{{ _app.language }}\" dir=\"{{ _app.text_direction }}\">\n<head>\n"
            "    <title>{{ _app.page_title }}</title>\n"
            "    <link rel=\"stylesheet\" href=\"/theme/bulma/assets/css/style.css?{{ _globals.cache_control }}\">\n\n"
            f"    {A.get('base-stylesheet', '')}\n</head>\n"
            "<body class=\"{{ _app.theme.is_dark_mode ? 'dark-mode' : 'default-mode' }}\">\n"
            "    {% block body_content %}{% endblock %}\n"
            f"    <script src=\"/theme/bulma/assets/js/main.js\"></script>\n{A.get('base-island-block', '</body>')}\n</html>\n"
        ),
        "layout/intern.twig": (
            f"{A.get('intern-island', '')}\n\n{{% block body_content %}}\n<header id=\"header\">\n"
            "    <a href=\"{{ _app.home_url }}\">\n"
            "        {% if _white_label.logo_intern_url %}\n            <img src=\"{{ _white_label.logo_intern_url }}\" alt=\"logo\">\n"
            f"        {{% else %}}\n            <figure>{A.get('intern-logo', '')}</figure>\n        {{% endif %}}\n    </a>\n"
            "</header>\n<section id=\"sidebar\">{% include 'components/nav.twig' %}</section>\n"
            "<div id=\"content\">{% block content %}{% endblock %}</div>\n{% endblock %}\n"
        ),
        "layout/extern.twig": (
            "{% extends 'layout/base.twig' %}\n\n{% block body_content %}\n"
            f"{A.get('extern-hero', '<section>')}\n    <div class=\"box\">\n"
            "        {% if _white_label.logo_extern_url %}\n            <img src=\"{{ _white_label.logo_extern_url }}\" alt=\"logo\">\n"
            f"        {{% else %}}\n            {A.get('extern-logo', '')}\n        {{% endif %}}\n"
            "        {% block content %}{% endblock %}\n    </div>\n</section>\n{% endblock %}\n"
        ),
        "layout/popup.twig": (
            "{% extends 'layout/base.twig' %}\n\n{% block body_content %}\n<header id=\"header\">\n"
            f"    {{% if _white_label.logo_intern_url %}}<img src=\"x\" alt=\"logo\">{{% else %}}{A.get('popup-logo', '')}{{% endif %}}\n"
            "</header>\n{% block content %}{% endblock %}\n{% endblock %}\n"
        ),
        "components/nav.twig": (
            "<nav id=\"sidebar-navigation\" class=\"menu\">\n{% for group in navigation %}\n"
            "    <p class=\"menu-label\">{{ group.label }}</p>\n{% endfor %}\n</nav>\n"
        ),
        "views/extern/login.twig": (
            "{% extends 'layout/extern.twig' %}\n\n{% block content %}\n    {# {% if %} inside a comment is ignored #}\n"
            "    <form method=\"post\">{{ csrf_field() }}</form>\n{% endblock %}\n"
        ),
        "views/intern/admin/dashboard.twig": (
            "{% extends 'layout/intern.twig' %}\n{% block content %}\n{% set rows = {'a': {'b': 1}} %}\n"
            "{% for k, v in rows %}{{ k }}{% else %}-{% endfor %}\n{% endblock %}\n"
        ),
    }
    known = set(files)
    for patch_id, (rel, anchor) in a.items():   # patches added later still get their anchor
        if rel not in known:
            files[rel] = files.get(rel, "") + anchor + "\n"
    return files


def tiny_png() -> bytes:
    raw = b"\x00\xff\xff\xff"
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def make_keyhelp(root: Path, *, version: str = "26.1.1", patches_dir: Path = PATCHES) -> Path:
    bulma = root / "theme" / "bulma"
    (bulma / "templates").mkdir(parents=True)
    (bulma / "_settings.json").write_text(json.dumps({
        "name": "Default Theme", "description": "fixture", "author": "test", "version": version,
        "website": "https://example.org", "path_to_templates": "templates/", "has_dark_mode": True,
    }, indent=4), encoding="utf-8")
    (bulma / "_screenshot.png").write_bytes(tiny_png())
    for rel, content in _templates(anchors(patches_dir)).items():
        path = bulma / "templates" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (root / "cache" / "twig").mkdir(parents=True)
    return root


def set_version(root: Path, version: str) -> None:
    path = root / "theme" / "bulma" / "_settings.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def make_assets(folder: Path, patches_dir: Path = PATCHES) -> Path:
    """Placeholder files for everything the build requires (no npm build needed)."""
    from lumen_panel.build import required_assets  # noqa: E402 (tests put generator/ on sys.path)
    from lumen_panel.patches import load_patches

    for rel in required_assets(load_patches(patches_dir)):
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".svg"):
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>\n', encoding="utf-8")
        else:
            path.write_text(f"/* {rel} */\n", encoding="utf-8")
    return folder


def compiled_entry(cache_dir: Path, name: str, source_path: str, logical: str = "layout/base.twig") -> Path:
    """A file shaped like a compiled Twig 3 template: only the parts the cache scan reads."""
    sub = cache_dir / name[:2]
    sub.mkdir(parents=True, exist_ok=True)
    path = sub / f"{name}.php"
    path.write_text(
        "<?php\n\nuse Twig\\Source;\n\n/* " + logical + " */\nclass __TwigTemplate_x extends Template\n{\n"
        "    public function getSourceContext()\n    {\n"
        f'        return new Source("", "{logical}", "{source_path}");\n    }}\n}}\n',
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":  # used by CI: python3 tests/fakekeyhelp.py <folder>
    import sys

    if len(sys.argv) != 2:
        sys.exit("usage: python3 tests/fakekeyhelp.py <new folder>")
    target = Path(sys.argv[1])
    if target.exists():
        sys.exit(f"{target}: already exists")
    make_keyhelp(target)
    print(f"fake panel tree written to {target}")
