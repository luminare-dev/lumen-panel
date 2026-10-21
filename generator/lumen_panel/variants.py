"""The two themes lumen-panel builds from the same local default theme.

    lumen       theme/lumen       "Lumen"       light; follows the panel's own dark-mode switch
                                                where the panel has one (has_dark_mode true)
    lumen-dark  theme/lumen-dark  "Lumen Dark"  always dark: lumen-panel's own dark design on top
                                                of the panel's standard (light) stylesheet

Lumen Dark is a dark design, not the panel's dark mode. Its _settings.json declares no dark mode
(has_dark_mode false), its patches load the default theme's standard stylesheet (style.css or
style-rtl.css) whatever the panel's dark-mode setting says, and nothing of it sets, reads for
styling or imitates the dark-mode switch, the dark stylesheets or the 'dark/' images of KeyHelp
Pro (docs/adr/0011-lumen-dark-is-a-design-not-the-pro-dark-mode.md).

Both variants are built the same way from one assets folder and one patch folder, and each keeps
its own theme folder, staging and parking names in theme/, backup folder (with its own run lock
and hold), build record and Twig cache entries: installing, updating, rolling back or removing
one never touches the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import THEME_DIR_NAME, THEME_DISPLAY_NAME

REPO_ROOT = Path(__file__).resolve().parents[2]
BRAND = REPO_ROOT / "assets" / "brand"

NOT_AFFILIATED = "Not affiliated with or endorsed by Keyweb AG. KeyHelp is a registered trademark of Keyweb AG."


@dataclass(frozen=True)
class Variant:
    name: str                       # the --variant value, also the theme folder below theme/
    display_name: str               # what Configuration -> Appearance -> Theme lists
    description: str                # _settings.json "description"
    has_dark_mode: bool             # _settings.json "has_dark_mode"
    stylesheets: tuple[str, ...]    # the stylesheets of dist/assets this variant loads
    screenshot_palette: str         # palette of the preview mock (screenshot.py)
    screenshot_lockup: str          # logo file below assets/ drawn into the preview
    screenshot_file: Path           # pre-rendered preview, copied without PyMuPDF
    patch_overlay: str | None = None   # subfolder of the patch folder with this variant's patches
    backup_subdir: str | None = None   # subfolder of the backup root (None: the root itself)

    @property
    def dir_name(self) -> str:
        return self.name

    @property
    def staging_prefix(self) -> str:
        return f".{self.name}-staging-"

    @property
    def parking_prefix(self) -> str:
        return f".{self.name}-previous-"

    @property
    def leftover_prefixes(self) -> tuple[str, str]:
        return (self.staging_prefix, self.parking_prefix)

    @property
    def cli_args(self) -> str:
        """What a printed command adds to select this variant ('' for the default)."""
        return "" if self is DEFAULT_VARIANT else f" --variant {self.name}"

    def backup_root(self, root: Path) -> Path:
        """Lumen keeps its backups in the backup root itself (as before Lumen Dark existed);
        every other variant in a subfolder of its own, with its own lock and hold."""
        return root / self.backup_subdir if self.backup_subdir else root


LUMEN = Variant(
    name=THEME_DIR_NAME,
    display_name=THEME_DISPLAY_NAME,
    description=("A modern theme for the KeyHelp hosting panel, a Luminare Development open-source project "
                 "(lumen-panel). " + NOT_AFFILIATED),
    has_dark_mode=True,
    stylesheets=("lumen.css", "lumen-dark.css", "lumen-rtl.css", "lumen-dark-rtl.css"),
    screenshot_palette="light",
    screenshot_lockup="brand/luminare-lockup-compact-light.svg",
    screenshot_file=BRAND / "theme-screenshot.png",
)

LUMEN_DARK = Variant(
    name="lumen-dark",
    display_name="Lumen Dark",
    description=("A modern theme for the KeyHelp hosting panel that is always dark, a Luminare Development "
                 "open-source project (lumen-panel). The dark design is lumen-panel's own stylesheet on top of "
                 "the panel's standard light stylesheet: it is not the dark mode of KeyHelp Pro and does not "
                 "enable, unlock or imitate it. " + NOT_AFFILIATED),
    has_dark_mode=False,
    stylesheets=("lumen-night.css", "lumen-night-rtl.css"),
    screenshot_palette="night",
    screenshot_lockup="brand/luminare-lockup-compact-dark.svg",
    screenshot_file=BRAND / "theme-screenshot-dark.png",
    patch_overlay="lumen-dark",
    backup_subdir="lumen-dark",
)

DEFAULT_VARIANT = LUMEN
VARIANTS: dict[str, Variant] = {v.name: v for v in (LUMEN, LUMEN_DARK)}
ALL_STYLESHEETS: frozenset[str] = frozenset(s for v in VARIANTS.values() for s in v.stylesheets)

# The default theme's dark-mode switch and assets, which a variant without a dark mode never uses
# in what lumen-panel adds (checked by verify and the tests): the switch variables, the dark
# stylesheets and the 'dark/' image folder.
PRO_DARK_MODE_MARKERS = ("is_dark_mode", "has_dark_mode", "style-dark", "dark/")


def get(name: str) -> Variant:
    try:
        return VARIANTS[name]
    except KeyError:
        raise ValueError(f"unknown variant {name!r}; one of: {', '.join(VARIANTS)}") from None


def by_dir_name(name: str) -> Variant | None:
    return next((v for v in VARIANTS.values() if v.dir_name == name), None)
