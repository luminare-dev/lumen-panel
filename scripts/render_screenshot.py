#!/usr/bin/env python3
"""Render the theme preview (assets/brand/theme-screenshot.png) with PyMuPDF.

The generator copies this file as _screenshot.png when PyMuPDF is not available on the server.
Run it with a Python that has PyMuPDF, for example the brand venv:

    /root/projects/.venvs/brand/bin/python scripts/render_screenshot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))

from lumen_panel.screenshot import render  # noqa: E402


def main() -> int:
    dest = ROOT / "assets" / "brand" / "theme-screenshot.png"
    render(dest, ROOT / "assets" / "brand" / "luminare-lockup-compact-light.svg")
    print(f"wrote {dest.relative_to(ROOT)} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
