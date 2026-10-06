"""Width of a line of text as the renderer will draw it.

ASS font sizes are line heights: a renderer scales the font so that its
ascent + descent equal the size. Measured with the real font file; checked
against Crunchyroll, whose dash dialogues are centred by hand (Trebuchet MS
bold 22 in a 640 grid: "– On contre-attaque !" gets MarginL 226, as here).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from bobinestyle.fonts import FontFace, faces_for, system_fonts

_REFERENCE_SIZE = 100
# Average advance of a Latin text in em, when the font is not installed.
_FALLBACK_ADVANCE = 0.55


@lru_cache(maxsize=16)
def _font(path: Path) -> tuple[ImageFont.FreeTypeFont, float]:
    font = ImageFont.truetype(str(path), _REFERENCE_SIZE)
    ascent, descent = font.getmetrics()
    return font, ascent + descent


def find_face(family: str, bold: bool, italic: bool) -> FontFace | None:
    """The face of ``family`` closest to the wanted weight and slant."""
    faces = faces_for(family.lower(), system_fonts())
    if not faces:
        return None

    def score(face: FontFace) -> int:
        names = " ".join(face.full_names)
        is_bold = "bold" in names or "gras" in names
        is_italic = "italic" in names or "oblique" in names
        return (is_bold == bold) * 2 + (is_italic == italic)

    return max(faces, key=score)


def text_width(text: str, family: str, size: float, bold: bool, italic: bool) -> float:
    """Width of ``text`` (one line, no tags) at ASS font size ``size``."""
    face = find_face(family, bold, italic)
    if face is None:
        return len(text) * size * _FALLBACK_ADVANCE
    font, height = _font(face.path)
    return font.getlength(text) * size / height


def centring_margin(lines: list[str], family: str, size: float, italic: bool, grid_width: float, minimum: float) -> int:
    """MarginL that centres a left-aligned block of ``lines`` (dash
    dialogue: the dashes stay aligned, the block sits in the middle)."""
    widest = max(text_width(line, family, size, True, italic) for line in lines)
    return round(max(minimum, (grid_width - widest) / 2))
