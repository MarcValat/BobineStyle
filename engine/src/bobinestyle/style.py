"""Apply the house style to an ASS script.

House values are pixels of a 16:9 1080p screen (see ``scale``). They are
converted into the script's own grid (PlayRes), which is kept whenever a
line carries coordinates or sizes of its own: changing the grid would move
or resize them. Only the style lines of dialogue roles and a few
[Script Info] keys are rewritten; every other line is kept as is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bobinestyle.ass import AssDocument, Event, Style, parse_ass
from bobinestyle.roles import DIALOGUE_ROLES, Role, ScriptReport, analyze
from bobinestyle.scale import screen_scale

FONT = "Trebuchet MS"
FONT_SIZE = 66
OUTLINE = 2.5
SHADOW = 2.5
MARGIN_SIDE = 6
MARGIN_V = 75
DASHES_EXTRA_LEFT = 60
MARGINS_EXTRA = 45

WHITE = "&H00FFFFFF"
RED = "&H000000FF"
BLACK = "&H00000000"
OVERLAP_YELLOW = "&H008CEEFA"  # RGB 250, 238, 140

# What renderers assume when a script has no PlayRes at all.
DEFAULT_PLAY_RES = (384, 288)

# Tags whose values are in PlayRes pixels: a line using one pins the grid.
_GEOMETRY_RE = re.compile(
    r"\\(?:pos|move|org|i?clip)\s*\(|\\p[1-9]|\\fs\d|\\fsp|\\[xy]?bord|\\[xy]?shad|\\be|\\blur"
)

_BORDER_TAG_RE = re.compile(r"\\[xy]?(?:bord|shad)")

# ASS numpad alignment back to SSA's numbering.
_ASS_TO_SSA_ALIGNMENT = {1: 1, 2: 2, 3: 3, 7: 5, 8: 6, 9: 7, 4: 9, 5: 10, 6: 11}


@dataclass
class StyleResult:
    text: str
    play_res: tuple[int, int]
    play_res_changed: bool
    report: ScriptReport
    restyled: list[tuple[str, Role]]
    warnings: list[str] = field(default_factory=list)


def _fmt(value: float) -> str:
    """Two decimals at most, no trailing zeros (22, 0.83)."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text if text != "-0" else "0"


def pins_grid(event: Event) -> bool:
    return bool(_GEOMETRY_RE.search(event.text))


def house_fields(role: Role, x: float, y: float) -> dict[str, str]:
    """The house style for ``role``, ``x``/``y`` converting reference-screen
    pixels into script units horizontally and vertically."""
    italic = role in (Role.ITALIC, Role.TOP_ITALIC, Role.DASHES_ITALIC)
    alignment = 8 if role in (Role.TOP, Role.TOP_ITALIC) else 1 if role in (Role.DASHES, Role.DASHES_ITALIC) else 2
    left = right = MARGIN_SIDE
    if role in (Role.DASHES, Role.DASHES_ITALIC):
        left += DASHES_EXTRA_LEFT
    if role is Role.MARGINS:
        left += MARGINS_EXTRA
        right += MARGINS_EXTRA
    return {
        "fontname": FONT,
        "fontsize": _fmt(FONT_SIZE * y),
        "primarycolour": OVERLAP_YELLOW if role is Role.OVERLAP else WHITE,
        "secondarycolour": RED,
        "outlinecolour": BLACK,
        "tertiarycolour": BLACK,
        "backcolour": BLACK,
        "bold": "-1",
        "italic": "-1" if italic else "0",
        "underline": "0",
        "strikeout": "0",
        "scalex": "100",
        "scaley": "100",
        "spacing": "0",
        "angle": "0",
        "borderstyle": "1",
        "outline": _fmt(OUTLINE * y),
        "shadow": _fmt(SHADOW * y),
        "alignment": str(alignment),
        "marginl": str(round(left * x)),
        "marginr": str(round(right * x)),
        "marginv": str(round(MARGIN_V * y)),
        "alphalevel": "0",
        "encoding": "1",
    }


def _style_line(style: Style, fields: dict[str, str]) -> str:
    merged = dict(style.fields)
    for name in merged:
        if name in fields and name != "name":
            merged[name] = fields[name]
    if style.ssa and "alignment" in merged:
        merged["alignment"] = str(_ASS_TO_SSA_ALIGNMENT[int(fields["alignment"])])
    return "Style: " + ",".join(merged.values())


def _event_line(event: Event, ratio_x: float, ratio_y: float) -> str:
    fields = dict(event.fields)
    for name, ratio in (("marginl", ratio_x), ("marginr", ratio_x), ("marginv", ratio_y)):
        value = fields.get(name, "").strip()
        if value.isdigit() and int(value):
            fields[name] = f"{round(int(value) * ratio):0{len(value)}d}"
    return f"{event.kind}: " + ",".join(fields.values())


def _set_info(lines: list[str], doc: AssDocument, key: str, value: str) -> None:
    """Replace ``key`` in [Script Info] or add it at the section's end."""
    start = next(i for i, l in enumerate(lines) if l.strip().lower() == "[script info]")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("[")), len(lines))
    for i in range(start + 1, end):
        name, sep, _ = lines[i].partition(":")
        if sep and name.strip().lower() == key.lower():
            lines[i] = f"{key}: {value}"
            return
    insert = end
    while insert > start + 1 and not lines[insert - 1].strip():
        insert -= 1
    lines.insert(insert, f"{key}: {value}")


def apply_house_style(text: str, video_size: tuple[int, int] | None) -> StyleResult:
    """``text`` restyled for a video shown at ``video_size`` (display
    pixels; None means 1080p)."""
    doc = parse_ass(text)
    report = analyze(doc)
    width, height = video_size or (1920, 1080)
    k = screen_scale(width, height)
    warnings: list[str] = []

    pinned = any(pins_grid(e) for e in doc.events if e.kind == "Dialogue")
    old = doc.play_res
    if pinned:
        play_res = old or DEFAULT_PLAY_RES
        if old and abs(old[0] / old[1] - width / height) > 0.01:
            warnings.append(
                f"PlayRes {old[0]}x{old[1]} n'a pas les proportions de la vidéo ({width}x{height}) : "
                "le texte peut être déformé, PlayRes conservé à cause du positionnement"
            )
    else:
        play_res = (width, height)
    changed = play_res != old

    lines = list(doc.lines)
    if not any(l.strip().lower() == "[script info]" for l in lines):
        lines[:0] = ["[Script Info]", "ScriptType: v4.00+", ""]
        doc = parse_ass("\n".join(lines))
    # Reference-screen pixels -> video pixels (k) -> script units.
    x = k * play_res[0] / width
    y = k * play_res[1] / height
    restyled = []
    by_name = {r.style.name: r for r in report.styles}
    for style in doc.styles:
        r = by_name.get(style.name)
        if r and r.role in DIALOGUE_ROLES and doc.style(style.name) is style:
            lines[style.line_index] = _style_line(style, house_fields(r.role, x, y))
            restyled.append((style.name, r.role))
    if changed:
        # Per-line margins are in the old grid (384x288 when there was none).
        before = old or DEFAULT_PLAY_RES
        ratio_x, ratio_y = play_res[0] / before[0], play_res[1] / before[1]
        for event in doc.events:
            if any(event.margins):
                lines[event.line_index] = _event_line(event, ratio_x, ratio_y)

    if not doc.scaled_border_and_shadow and any(_BORDER_TAG_RE.search(e.text) for e in doc.events):
        warnings.append(
            "ScaledBorderAndShadow passe à yes : les contours et ombres fixés dans les lignes changent d'épaisseur"
        )
    _set_info(lines, doc, "ScaledBorderAndShadow", "yes")
    if changed:
        _set_info(lines, doc, "PlayResX", str(play_res[0]))
        _set_info(lines, doc, "PlayResY", str(play_res[1]))
    if not restyled:
        warnings.append("aucun style de dialogue : seuls les en-têtes ont été modifiés")
    return StyleResult("\n".join(lines) + "\n", play_res, changed, report, restyled, warnings)
