"""The preview image KeyHelp shows under Configuration -> Appearance -> Theme (``_screenshot.png``).

With PyMuPDF available (for example the brand venv), a mock of the panel is drawn from the
design tokens and the Luminare lockup: light for Lumen, the night colours for Lumen Dark.
Without it, the pre-rendered image of the variant is copied (``assets/brand/theme-screenshot.png``
or ``assets/brand/theme-screenshot-dark.png``). ``scripts/render_screenshot.py`` refreshes both.
"""

from __future__ import annotations

import shutil
from pathlib import Path

WIDTH, HEIGHT = 500, 250   # the default theme's preview size (points; rendered at 2x)

LIGHT = {"bg": "#F3F6FB", "surface": "#FFFFFF", "border": "#E3E8F1", "text": "#0A1224",
         "muted": "#B7C1D3", "primary": "#1F47C4", "tint": "#E9EDF9", "success": "#028844"}
# Lumen Dark: the dark token set (src/styles/tokens.css), always on.
NIGHT = {"bg": "#0A1224", "surface": "#10182B", "border": "#303A4F", "text": "#F3F6FB",
         "muted": "#39445C", "primary": "#5BDFFF", "tint": "#142B3E", "success": "#58DD70"}
PALETTES = {"light": LIGHT, "night": NIGHT}


def _rgb(hex_colour: str) -> tuple[float, float, float]:
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def render(dest: Path, lockup_svg: Path, scale: float = 2.0, palette: str = "light") -> None:
    import pymupdf  # optional dependency, only for this function

    c = {k: _rgb(v) for k, v in PALETTES[palette].items()}
    doc = pymupdf.open()
    page = doc.new_page(width=WIDTH, height=HEIGHT)

    def rect(x0, y0, x1, y1, fill, radius=0.0, stroke=None):
        r = pymupdf.Rect(x0, y0, x1, y1)
        shape = page.new_shape()
        if radius:
            shape.draw_rect(r, radius=radius / min(r.width, r.height))
        else:
            shape.draw_rect(r)
        shape.finish(color=stroke, fill=fill, width=0.6 if stroke else 0)
        shape.commit()

    rect(0, 0, WIDTH, HEIGHT, c["bg"])
    # header and sidebar
    rect(0, 0, WIDTH, 30, c["surface"])
    rect(0, 29.4, WIDTH, 30, c["border"])
    rect(0, 30, 112, HEIGHT, c["surface"])
    rect(111.4, 30, 112, HEIGHT, c["border"])
    svg = pymupdf.open(stream=lockup_svg.read_bytes(), filetype="svg")
    logo = pymupdf.open("pdf", svg.convert_to_pdf())
    page.show_pdf_page(pymupdf.Rect(6, 3, 6 + 24 * 3.017, 27), logo, 0)
    # sidebar items, one active
    for i in range(7):
        y = 44 + i * 22
        if i == 1:
            rect(8, y - 5, 104, y + 11, c["tint"], radius=4)
            rect(14, y + 1, 70, y + 5, c["primary"], radius=2)
        else:
            rect(14, y + 1, 60 + (i * 7) % 30, y + 5, c["muted"], radius=2)
    # page title and cards
    rect(126, 44, 220, 52, c["text"], radius=2)
    for col, (x0, x1) in enumerate(((126, 300), (310, 486))):
        rect(x0, 64, x1, 236, c["surface"], radius=7, stroke=c["border"])
        rect(x0 + 12, 76, x0 + 80, 82, c["text"], radius=2)
        rect(x0, 92, x1, 92.6, c["border"])
        for row in range(5):
            y = 104 + row * 24
            rect(x0 + 12, y, x0 + 60, y + 4, c["muted"], radius=2)
            if col == 0:
                rect(x0 + 80, y, x1 - 14, y + 4, c["border"], radius=2)
                rect(x0 + 80, y, x0 + 80 + (x1 - x0 - 94) * (0.3 + row * 0.12), y + 4, c["success"], radius=2)
            else:
                rect(x0 + 80, y, x0 + 120 + row * 6, y + 4, c["muted"], radius=2)
        rect(x1 - 70, 212, x1 - 12, 228, c["primary"], radius=5)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(dest))


def write_screenshot(dest: Path, *, lockup_svg: Path | None, fallback: Path, palette: str = "light") -> str:
    """Render the preview if PyMuPDF is importable, otherwise copy the pre-rendered fallback."""
    if lockup_svg is not None and lockup_svg.is_file():
        try:
            render(dest, lockup_svg, palette=palette)
            return "rendered"
        except ImportError:
            pass
    if not fallback.is_file():
        raise FileNotFoundError(f"{fallback}: pre-rendered screenshot missing")
    shutil.copyfile(fallback, dest)
    return "copied"
