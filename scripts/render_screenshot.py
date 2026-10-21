#!/usr/bin/env python3
"""Render the theme previews with PyMuPDF: assets/brand/theme-screenshot.png (Lumen, light) and
assets/brand/theme-screenshot-dark.png (Lumen Dark, the night colours).

The generator copies the variant's file as _screenshot.png when PyMuPDF is not available on the
server. Run it with a Python that has PyMuPDF (pip install pymupdf):

    python scripts/render_screenshot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))

from lumen_panel.screenshot import render  # noqa: E402
from lumen_panel.variants import VARIANTS  # noqa: E402


def main() -> int:
    for variant in VARIANTS.values():
        dest = variant.screenshot_file
        render(dest, ROOT / "assets" / variant.screenshot_lockup, palette=variant.screenshot_palette)
        print(f"wrote {dest.relative_to(ROOT)} ({dest.stat().st_size} bytes, {variant.display_name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
