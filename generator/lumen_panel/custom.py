"""A customization: the files a Lumen token file compiles to (customizer ZIP or tokens/compile.mjs).

Folder layout (``custom/`` in the checkout by default, see --custom):

    lumen.tokens.json     the token set (only read for its name; the CSS is already compiled)
    override-follow.css   appended to lumen.css and lumen-rtl.css (Lumen follows the panel's dark mode)
    override-dark.css     appended to lumen-dark*.css and to both Lumen Dark stylesheets
    branding.json         logos and favicon for the template patches
    README.txt            optional
    custom/<file>         uploaded logos, images and fonts (copied to theme/<variant>/assets/custom/)

Everything is checked before a build uses it, because the files end up below the panel's public
web root and in its templates: only these names, image and font types, size limits, SVG files
without scripts or external references, and branding values that are a shipped logo, an uploaded
file, an https URL or empty.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .variants import Variant

TOP_FILES = {"lumen.tokens.json", "override-follow.css", "override-dark.css", "branding.json"}
OPTIONAL_FILES = {"README.txt"}
MEDIA_DIR = "custom"
MEDIA_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".svg", ".woff", ".woff2"}
MAX_MEDIA = 4 * 1024 * 1024
MAX_CSS = 512 * 1024
MAX_TOTAL = 24 * 1024 * 1024
MAX_FILES = 64
BRANDING_KEYS = ("headerLight", "headerDark", "loginLight", "loginDark", "favicon", "productName")
CSS_HEAD = "/* Lumen tokens v1: "
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
HTTPS_RE = re.compile(r"^https://[A-Za-z0-9._~:/?#\[\]@!$&*+,;=%-]+$")
SVG_FORBIDDEN = re.compile(
    rb"<script|<foreignobject|<!entity|<!doctype|<use\b|<animate|<set\b|\son[a-z]+\s*=|javascript:|@import|"
    rb"(?:href|src)\s*=\s*[\"'](?!#)|url\(\s*[\"']?(?!#)",
    re.IGNORECASE)

# stylesheet of the theme -> the override appended to it (tokens/keyhelp.ts STYLESHEET_KINDS)
STYLESHEET_KINDS = {
    "lumen.css": "follow",
    "lumen-rtl.css": "follow",
    "lumen-dark.css": "dark",
    "lumen-dark-rtl.css": "dark",
    "lumen-night.css": "dark",
    "lumen-night-rtl.css": "dark",
}

# KeyHelp's own logo, which the logo patches replace: an empty logo puts it back in Lumen. It is
# loaded from the default theme's folder (base_url: /theme/default, or /theme/bulma before 26.2).
def keyhelp_logo(base_url: str) -> str:
    return (f"<img src=\"{base_url}/assets/img/{{{{ _app.theme.is_dark_mode ? 'dark/' }}}}keyhelp"
            "{{ _app.is_pro ? '-pro' }}.svg?{{ _globals.cache_control }}\" alt=\"logo\">")


KEYHELP_LOGO = keyhelp_logo("/theme/default")
LOCKUP_SIZE = {"header": (127, 42), "login": (300, 114)}


class CustomError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("customization rejected:\n  " + "\n  ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Custom:
    folder: Path
    name: str
    sha256: str
    css: dict[str, str]            # "follow" / "dark" -> CSS text
    branding: dict[str, str]
    media: tuple[str, ...] = field(default=())   # file names below custom/


def _sha(folder: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in files:
        digest.update(rel.encode("utf-8") + b"\0" + hashlib.sha256((folder / rel).read_bytes()).digest())
    return digest.hexdigest()


def _files(folder: Path, problems: list[str]) -> list[str]:
    out: list[str] = []
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            problems.append(f"{rel}: symbolic links are not allowed")
        elif stat.S_ISDIR(mode):
            if rel != MEDIA_DIR:
                problems.append(f"{rel}/: unexpected folder")
        elif rel in TOP_FILES or rel in OPTIONAL_FILES:
            out.append(rel)
        elif rel.startswith(MEDIA_DIR + "/") and "/" not in rel[len(MEDIA_DIR) + 1:]:
            name = rel[len(MEDIA_DIR) + 1:]
            if not NAME_RE.match(name) or name.startswith(".") or Path(name).suffix.lower() not in MEDIA_TYPES:
                problems.append(f"{rel}: only images (png, jpg, webp, gif, ico, svg) and fonts (woff, woff2) "
                                "with plain names are allowed")
            else:
                out.append(rel)
        else:
            problems.append(f"{rel}: unexpected file")
    return out


def _check_media(folder: Path, rel: str, problems: list[str]) -> None:
    data = (folder / rel).read_bytes()
    if len(data) > MAX_MEDIA:
        problems.append(f"{rel}: larger than {MAX_MEDIA // (1024 * 1024)} MB")
        return
    suffix = Path(rel).suffix.lower()
    magic = {
        ".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",),
        ".gif": (b"GIF87a", b"GIF89a"), ".ico": (b"\x00\x00\x01\x00",), ".woff": (b"wOFF",), ".woff2": (b"wOF2",),
    }
    if suffix == ".webp":
        ok = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    elif suffix == ".svg":
        ok = b"<svg" in data[:4096].lower() and not SVG_FORBIDDEN.search(data)
        if not ok:
            problems.append(f"{rel}: not an SVG, or it contains scripts, event handlers, <use>, animations, "
                            "entities or references outside the file")
            return
    else:
        ok = data.startswith(magic[suffix])
    if not ok:
        problems.append(f"{rel}: content does not match the {suffix} type")


def _check_branding(value: object, key: str, media: set[str], assets_dir: Path, problems: list[str]) -> str:
    if not isinstance(value, str):
        problems.append(f"branding.json: {key} must be a string")
        return ""
    if key == "productName":
        if len(value) > 60 or re.search(r"[<>{}]", value):
            problems.append("branding.json: productName must be at most 60 characters without < > { }")
            return ""
        return value
    if value == "":
        return ""
    if value.startswith(MEDIA_DIR + "/"):
        if value[len(MEDIA_DIR) + 1:] not in media:
            problems.append(f"branding.json: {key} names {value}, which is not in the customization")
        return value
    if value.startswith("brand/"):
        name = value[len("brand/"):]
        if not NAME_RE.match(name) or not name.endswith(".svg") or not (assets_dir / value).is_file():
            problems.append(f"branding.json: {key} names {value}, which is not a shipped logo")
        return value
    if len(value) <= 2048 and HTTPS_RE.match(value) and "{" not in value and "}" not in value:
        return value
    problems.append(f"branding.json: {key} must be brand/<file>.svg, custom/<file>, an https URL or empty")
    return ""


def load(folder: Path, assets_dir: Path) -> Custom:
    """Check a customization folder and read it; raises CustomError listing every problem."""
    problems: list[str] = []
    if not folder.is_dir():
        raise CustomError([f"{folder}: not a folder"])
    files = _files(folder, problems)
    missing = sorted(TOP_FILES - set(files))
    problems += [f"{name}: missing" for name in missing]
    media = [rel[len(MEDIA_DIR) + 1:] for rel in files if rel.startswith(MEDIA_DIR + "/")]
    if len(files) > MAX_FILES:
        problems.append(f"more than {MAX_FILES} files")
    if sum((folder / rel).stat().st_size for rel in files) > MAX_TOTAL:
        problems.append(f"larger than {MAX_TOTAL // (1024 * 1024)} MB in total")
    if problems:
        raise CustomError(problems)
    for name in media:
        _check_media(folder, f"{MEDIA_DIR}/{name}", problems)
    css: dict[str, str] = {}
    for kind in ("follow", "dark"):
        rel = f"override-{kind}.css"
        raw = (folder / rel).read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{rel}: not UTF-8")
            continue
        if len(raw) > MAX_CSS or not text.startswith(CSS_HEAD) or re.search(r"</\s*style", text, re.IGNORECASE):
            problems.append(f"{rel}: not a compiled Lumen override (it must start with '{CSS_HEAD.strip()}', "
                            f"stay below {MAX_CSS // 1024} KB and contain no </style>)")
            continue
        css[kind] = text
    try:
        tokens = json.loads((folder / "lumen.tokens.json").read_text(encoding="utf-8"))
        name = str(tokens.get("meta", {}).get("name", ""))[:200] if isinstance(tokens, dict) else ""
        if not isinstance(tokens, dict) or tokens.get("version") != 1:
            problems.append("lumen.tokens.json: not a Lumen token file of version 1")
    except (ValueError, UnicodeDecodeError):
        problems.append("lumen.tokens.json: not valid JSON")
        name = ""
    branding: dict[str, str] = {}
    try:
        raw_branding = json.loads((folder / "branding.json").read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        raw_branding = None
    if not isinstance(raw_branding, dict) or set(raw_branding) != set(BRANDING_KEYS):
        problems.append(f"branding.json: must be an object with exactly {', '.join(BRANDING_KEYS)}")
    else:
        for key in BRANDING_KEYS:
            branding[key] = _check_branding(raw_branding[key], key, set(media), assets_dir, problems)
    if problems:
        raise CustomError(problems)
    return Custom(folder=folder, name=re.sub(r"[^\x20-\x7e]", "", name), sha256=_sha(folder, files),
                  css=css, branding=branding, media=tuple(media))


def extract_zip(zip_path: Path, dest: Path) -> Path:
    """Unpack a customizer ZIP into ``dest`` (a new, empty folder) without trusting its paths.

    The files may sit at the top or inside one folder; returns the folder holding lumen.tokens.json."""
    problems: list[str] = []
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise CustomError([f"{zip_path}: not a ZIP file ({exc})"]) from exc
    with archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        if len(infos) > MAX_FILES:
            raise CustomError([f"{zip_path}: more than {MAX_FILES} files"])
        if sum(i.file_size for i in infos) > MAX_TOTAL:
            raise CustomError([f"{zip_path}: larger than {MAX_TOTAL // (1024 * 1024)} MB unpacked"])
        names = [i.filename for i in infos]
        prefix = ""
        if names and all("/" in n for n in names):
            first = names[0].split("/", 1)[0] + "/"
            if all(n.startswith(first) for n in names) and any(n == first + "lumen.tokens.json" for n in names):
                prefix = first
        for info in infos:
            rel = info.filename[len(prefix):]
            parts = rel.split("/")
            if (info.filename.startswith("/") or "\\" in rel or any(p in ("", ".", "..") for p in parts)
                    or len(parts) > 2 or (info.external_attr >> 16) & 0o170000 == 0o120000):
                problems.append(f"{info.filename}: unsafe path or link")
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, open(target, "xb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
    if problems:
        raise CustomError(problems)
    return dest


def read_source(path: Path, assets_dir: Path, tmp: Path) -> Custom:
    """A ZIP or a customization folder (for example a backup), checked."""
    if path.is_dir():
        return load(path, assets_dir)
    folder = tmp / "unpacked"
    folder.mkdir()
    extract_zip(path, folder)
    return load(folder, assets_dir)


def copy_to(custom: Custom, dest: Path) -> None:
    """Write a checked customization to ``dest`` (a new folder): exactly the files that were checked."""
    dest.mkdir(parents=True)
    for name in sorted(TOP_FILES | OPTIONAL_FILES):
        if (custom.folder / name).is_file():
            shutil.copyfile(custom.folder / name, dest / name)
    if custom.media:
        (dest / MEDIA_DIR).mkdir()
        for name in custom.media:
            shutil.copyfile(custom.folder / MEDIA_DIR / name, dest / MEDIA_DIR / name)


# ---------------------------------------------------------------------------------------------
# What a build does with it
# ---------------------------------------------------------------------------------------------

def _src(value: str, theme_dir: str, cache: str) -> str:
    if value.startswith("https://"):
        return html.escape(value, quote=True)
    return f"/theme/{theme_dir}/assets/{value}?v={cache}"


def _img(value: str, place: str, alt: str, theme_dir: str, cache: str) -> str:
    size = ""
    if value.startswith("brand/luminare-lockup-"):
        w, h = LOCKUP_SIZE[place]
        size = f' width="{w}" height="{h}"'
    return (f'<img class="lumen-logo lumen-logo--{place}" src="{_src(value, theme_dir, cache)}"{size} '
            f'alt="{alt}">')


def _alt(branding: dict[str, str], value: str) -> str:
    name = branding.get("productName", "")
    if not name:
        name = "Luminare Development" if value.startswith("brand/luminare-") else "Logo"
    return html.escape(name, quote=True).replace("{", "&#123;").replace("}", "&#125;")


DEFAULT_BRANDING = {
    "headerLight": "brand/luminare-lockup-compact-light.svg",
    "headerDark": "brand/luminare-lockup-compact-dark.svg",
    "loginLight": "brand/luminare-lockup-horizontal-light.svg",
    "loginDark": "brand/luminare-lockup-horizontal-dark.svg",
    "favicon": "",
    "productName": "",
}


def logo_html(variant: Variant, place: str, branding: dict[str, str] | None, theme_dir: str, cache: str,
              base_url: str = "/theme/default") -> str:
    """The markup the header or login logo patch puts in place of KeyHelp's logo."""
    if branding is None:  # no customization: the Luminare lockups, as before customizations existed
        b = DEFAULT_BRANDING
        if variant.has_dark_mode:
            stem = "compact" if place == "header" else "horizontal"
            w, h = LOCKUP_SIZE[place]
            return (f'<img class="lumen-logo lumen-logo--{place}" src="/theme/{theme_dir}/assets/brand/luminare-lockup-'
                    f"{stem}-{{{{ _app.theme.is_dark_mode ? 'dark' : 'light' }}}}.svg?v={cache}\" width=\"{w}\" "
                    f'height="{h}" alt="Luminare Development">')
    else:
        b = branding
    light, dark = b[f"{place}Light"], b[f"{place}Dark"]
    if not variant.has_dark_mode:
        if dark == "":
            name = html.escape(b.get("productName") or "KeyHelp")
            return f'<span class="lumen-logo lumen-logo--{place} lumen-logo--text">{name}</span>'
        return _img(dark, place, _alt(b, dark), theme_dir, cache)
    if light == "" and dark == "":
        return keyhelp_logo(base_url)
    if light == dark:
        return _img(light, place, _alt(b, light), theme_dir, cache)
    return ("{% if _app.theme.is_dark_mode %}" + _img(dark, place, _alt(b, dark), theme_dir, cache)
            + "{% else %}" + _img(light, place, _alt(b, light), theme_dir, cache) + "{% endif %}")


FAVICON_ANCHOR = "{% if _white_label.favicon_url %}"


def favicon_html(branding: dict[str, str] | None, theme_dir: str, cache: str) -> str:
    """Replaces the start of the favicon block: a customization's favicon wins over the white-label
    favicon and KeyHelp's; without one the block stays as it is."""
    value = (branding or {}).get("favicon", "")
    if value == "":
        return FAVICON_ANCHOR
    kind = {".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}.get(Path(value.split("?")[0]).suffix.lower(), "")
    type_attr = f' type="{kind}"' if kind else ""
    return (f'{{% if true %}}<link rel="icon"{type_attr} href="{_src(value, theme_dir, cache)}">'
            "{% elseif _white_label.favicon_url %}")


def substitutions(variant: Variant, custom: Custom | None, theme_dir: str, cache: str,
                  base_url: str = "/theme/default") -> dict[str, str]:
    b = custom.branding if custom else None
    return {
        "LUMEN_HEADER_LOGO": logo_html(variant, "header", b, theme_dir, cache, base_url),
        "LUMEN_LOGIN_LOGO": logo_html(variant, "login", b, theme_dir, cache, base_url),
        "LUMEN_FAVICON": favicon_html(b, theme_dir, cache),
    }


def apply_to_assets(custom: Custom, assets_out: Path, stylesheets: tuple[str, ...]) -> None:
    """Append the overrides to the theme's stylesheets and copy the uploads to assets/custom/."""
    for name in stylesheets:
        kind = STYLESHEET_KINDS[name]
        path = assets_out / name
        css = path.read_text(encoding="utf-8")
        path.write_text(css.rstrip("\n") + "\n" + custom.css[kind], encoding="utf-8")
    if custom.media:
        (assets_out / MEDIA_DIR).mkdir(exist_ok=True)
        for name in custom.media:
            shutil.copyfile(custom.folder / MEDIA_DIR / name, assets_out / MEDIA_DIR / name)


def new_temp_dir() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="lumen-custom-")
