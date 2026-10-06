"""Find the fonts a script needs on this computer, to attach them to the MKV.

Fonts are matched by the names stored inside the files (family and full
name), as renderers do, not by file name: ``trebucbd.ttf`` is
"Trebuchet MS" / "Trebuchet MS Bold".
"""

from __future__ import annotations

import os
import re
import struct
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bobinestyle.ass import AssDocument

FONT_EXTENSIONS = (".ttf", ".otf", ".ttc", ".otc")

# The legacy Matroska font types: older players (and older Plex
# transcoders) ignore attachments typed font/ttf.
MIMETYPES = {
    ".ttf": "application/x-truetype-font",
    ".ttc": "application/x-truetype-font",
    ".otf": "application/vnd.ms-opentype",
    ".otc": "application/vnd.ms-opentype",
}

_FN_RE = re.compile(r"\\fn([^\\}]*)")


@dataclass(frozen=True)
class FontFace:
    path: Path
    families: frozenset[str]  # lowercase
    full_names: frozenset[str]  # lowercase


def _decode(raw: bytes, platform: int) -> str | None:
    try:
        return raw.decode("utf-16-be") if platform in (0, 3) else raw.decode("latin-1")
    except UnicodeDecodeError:
        return None


def _names_at(data: bytes, offset: int) -> tuple[set[str], set[str]]:
    """Family (IDs 1 and 16) and full (ID 4) names of the font at ``offset``."""
    families: set[str] = set()
    full: set[str] = set()
    num_tables = struct.unpack_from(">H", data, offset + 4)[0]
    for i in range(num_tables):
        tag, _, table_offset, _ = struct.unpack_from(">4sIII", data, offset + 12 + 16 * i)
        if tag != b"name":
            continue
        _, count, strings = struct.unpack_from(">HHH", data, table_offset)
        for j in range(count):
            platform, _, _, name_id, length, string_offset = struct.unpack_from(
                ">HHHHHH", data, table_offset + 6 + 12 * j
            )
            if name_id not in (1, 4, 16):
                continue
            start = table_offset + strings + string_offset
            name = _decode(data[start : start + length], platform)
            if name and name.strip():
                (full if name_id == 4 else families).add(name.strip().lower())
        break
    return families, full


def read_font_names(path: Path) -> list[tuple[set[str], set[str]]]:
    """(families, full names) of each font in a TTF/OTF file or collection."""
    try:
        data = path.read_bytes()
        if data[:4] == b"ttcf":
            count = struct.unpack_from(">I", data, 8)[0]
            offsets = struct.unpack_from(f">{count}I", data, 12)
        else:
            offsets = (0,)
        return [_names_at(data, o) for o in offsets]
    except (OSError, struct.error):
        return []


def font_faces(path: Path) -> FontFace | None:
    names = read_font_names(path)
    if not names:
        return None
    families = frozenset(n for fam, _ in names for n in fam)
    full = frozenset(n for _, f in names for n in f)
    return FontFace(path, families, full) if families else None


def system_font_dirs() -> list[Path]:
    home = Path.home()
    if sys.platform == "win32":
        dirs = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
        if local := os.environ.get("LOCALAPPDATA"):
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        dirs = [Path("/System/Library/Fonts"), Path("/Library/Fonts"), home / "Library" / "Fonts"]
    else:
        dirs = [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), home / ".local/share/fonts", home / ".fonts"]
    return [d for d in dirs if d.is_dir()]


@lru_cache(maxsize=4)
def font_index(dirs: tuple[Path, ...]) -> tuple[FontFace, ...]:
    faces = []
    for folder in dirs:
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() in FONT_EXTENSIONS and (face := font_faces(path)):
                faces.append(face)
    return tuple(faces)


def system_fonts() -> tuple[FontFace, ...]:
    return font_index(tuple(system_font_dirs()))


def fonts_used(doc: AssDocument) -> set[str]:
    """Font names (lowercase) the script's lines may render with: their
    styles' fonts and every ``\\fn`` override."""
    used_styles = {e.style for e in doc.events if e.kind == "Dialogue"}
    names = {s.fontname for s in doc.styles if s.name in used_styles}
    for event in doc.events:
        if event.kind == "Dialogue":
            names.update(m.group(1) for m in _FN_RE.finditer(event.text))
    # "@Font" is the same font laid out vertically.
    return {n.strip().lstrip("@").lower() for n in names if n.strip().lstrip("@")}


def faces_for(name: str, faces: tuple[FontFace, ...]) -> list[FontFace]:
    """Every face of the family ``name`` (all weights and slants), or the
    single face whose full name it is."""
    family = [f for f in faces if name in f.families]
    return family or [f for f in faces if name in f.full_names]
