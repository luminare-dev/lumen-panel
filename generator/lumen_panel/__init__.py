"""lumen-panel: builds the Lumen theme for the KeyHelp hosting panel from the local default theme.

The theme is assembled on the server: the default theme's templates are copied from the locally
licensed KeyHelp install, a small set of patches (patches/*.json) is applied, and the project's
own assets (CSS, fonts, logo, command palette) are added. No KeyHelp file is part of this
package.
"""

__version__ = "0.1.0"  # x-release-please-version

THEME_DIR_NAME = "lumen"
THEME_DISPLAY_NAME = "Lumen"
BASE_THEME_DIR_NAME = "bulma"
