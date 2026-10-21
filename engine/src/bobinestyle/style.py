"""Apply a style (the house style, or one of the user's) to an ASS script.

A style's values are pixels of a 16:9 1080p screen (see ``scale``). They are
converted into the script's own grid (PlayRes), which is kept whenever a
line carries coordinates or sizes of its own: changing the grid would move
or resize them. Only the style lines of dialogue roles and a few
[Script Info] keys are rewritten; every other line is kept as is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bobinestyle.ass import AssDocument, Event, Style, parse_ass
from bobinestyle.i18n import tr
from bobinestyle.measure import centring_margin
from bobinestyle.roles import DIALOGUE_ROLES, Role, ScriptReport, analyze
from bobinestyle.scale import screen_scale
from bobinestyle.styles import HOUSE, SubtitleStyle, ass_color

# The house style's font, the one every style starts from.
FONT = HOUSE.font
# A dash block's room on the left, beyond the side margin: it's centred by
# its MarginL (see _centre_dash_blocks) when it has none of its own.
DASHES_EXTRA_LEFT = 60

# Karaoke's colour, which the dialogue never uses.
RED = "&H000000FF"

# What renderers assume when a script has no PlayRes at all.
DEFAULT_PLAY_RES = (384, 288)

# Tags whose values are in PlayRes pixels: a line using one pins the grid.
_GEOMETRY_RE = re.compile(r"\\(?:pos|move|org|i?clip)\s*\(|\\p[1-9]|\\fs\d|\\fsp|\\[xy]?bord|\\[xy]?shad|\\be|\\blur")

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
    notes: list[str] = field(default_factory=list)


def _fmt(value: float) -> str:
    """Two decimals at most, no trailing zeros (22, 0.83)."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text if text != "-0" else "0"


def pins_grid(event: Event) -> bool:
    return bool(_GEOMETRY_RE.search(event.text))


def is_dashes(role: Role, style: SubtitleStyle) -> bool:
    """A dash block, laid out as one (its variant on)."""
    return style.dashes_variant and role in (Role.DASHES, Role.DASHES_ITALIC)


def house_fields(role: Role, x: float, y: float, style: SubtitleStyle = HOUSE) -> dict[str, str]:
    """``style``'s look for ``role``, ``x``/``y`` converting reference-screen
    pixels into script units horizontally and vertically. A variant turned
    off leaves the role the dialogue's look."""
    italic_role = role in (Role.ITALIC, Role.TOP_ITALIC, Role.DASHES_ITALIC)
    italic = (not style.italic) if italic_role and style.italic_variant else style.italic
    top = style.top_variant and role in (Role.TOP, Role.TOP_ITALIC)
    dashes = is_dashes(role, style)
    alignment = 8 if top else 1 if dashes else 2
    left = right = style.margin_side
    if dashes:
        left += DASHES_EXTRA_LEFT
    if style.margins_variant and role is Role.MARGINS:
        left += style.margins_extra
        right += style.margins_extra
    overlap = style.overlap_variant and role is Role.OVERLAP
    return {
        "fontname": style.font,
        "fontsize": _fmt(style.size * y),
        "primarycolour": ass_color(style.overlap_color if overlap else style.color),
        "secondarycolour": RED,
        "outlinecolour": ass_color(style.outline_color),
        "tertiarycolour": ass_color(style.outline_color),
        "backcolour": ass_color(style.shadow_color),
        "bold": "-1" if style.bold else "0",
        "italic": "-1" if italic else "0",
        "underline": "0",
        "strikeout": "0",
        "scalex": "100",
        "scaley": "100",
        "spacing": "0",
        "angle": "0",
        "borderstyle": "1",
        "outline": _fmt(style.outline * y),
        "shadow": _fmt(style.shadow * y),
        "alignment": str(alignment),
        "marginl": str(round(left * x)),
        "marginr": str(round(right * x)),
        "marginv": str(round((style.top_margin if top else style.margin_bottom) * y)),
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
    start = next(i for i, line in enumerate(lines) if line.strip().lower() == "[script info]")
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


def apply_house_style(text: str, video_size: tuple[int, int] | None, style: SubtitleStyle = HOUSE) -> StyleResult:
    """``text`` restyled in ``style`` for a video shown at ``video_size``
    (display pixels; None means 1080p)."""
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
                tr(
                    "PlayRes {old_width}x{old_height} n'a pas les proportions de la vidéo ({width}x{height}) : "
                    "le texte peut être déformé, PlayRes conservé à cause du positionnement",
                    old_width=old[0],
                    old_height=old[1],
                    width=width,
                    height=height,
                )
            )
    else:
        play_res = (width, height)
    changed = play_res != old

    lines = list(doc.lines)
    if not any(line.strip().lower() == "[script info]" for line in lines):
        lines[:0] = ["[Script Info]", "ScriptType: v4.00+", ""]
        doc = parse_ass("\n".join(lines))
    # Reference-screen pixels -> video pixels (k) -> script units.
    x = k * play_res[0] / width
    y = k * play_res[1] / height
    restyled = []
    by_name = {r.style.name: r for r in report.styles}
    for line_style in doc.styles:
        r = by_name.get(line_style.name)
        if r and r.role in DIALOGUE_ROLES and doc.style(line_style.name) is line_style:
            lines[line_style.line_index] = _style_line(line_style, house_fields(r.role, x, y, style))
            restyled.append((line_style.name, r.role))
    if changed:
        # Per-line margins are in the old grid (384x288 when there was none).
        before = old or DEFAULT_PLAY_RES
        ratio_x, ratio_y = play_res[0] / before[0], play_res[1] / before[1]
        for event in doc.events:
            if any(event.margins):
                lines[event.line_index] = _event_line(event, ratio_x, ratio_y)

    centred = _centre_dash_blocks(doc, lines, by_name, play_res[0], x, y, style)

    if not doc.scaled_border_and_shadow and any(_BORDER_TAG_RE.search(e.text) for e in doc.events):
        warnings.append(
            tr("ScaledBorderAndShadow passe à yes : les contours et ombres fixés dans les lignes changent d'épaisseur")
        )
    _set_info(lines, doc, "ScaledBorderAndShadow", "yes")
    if changed:
        _set_info(lines, doc, "PlayResX", str(play_res[0]))
        _set_info(lines, doc, "PlayResY", str(play_res[1]))
    if not restyled:
        warnings.append(tr("aucun style de dialogue : seuls les en-têtes ont été modifiés"))
    notes = [tr("{count} réplique(s) à tirets centrée(s) par leur marge", count=centred)] if centred else []
    return StyleResult("\n".join(lines) + "\n", play_res, changed, report, restyled, warnings, notes)


_PLACED_RE = re.compile(r"\\(?:pos|move)\s*\(|\\an[1-9]")


def _centre_dash_blocks(
    doc: AssDocument, lines: list[str], by_name: dict, grid_width: int, x: float, y: float, style: SubtitleStyle
) -> int:
    """Give dash-dialogue lines that have no MarginL of their own the one
    that centres their block, as Crunchyroll does by hand: the dash style
    is left-aligned, so without it the block would hug the left edge.
    Returns how many lines were centred."""
    count = 0
    for event in doc.events:
        report = by_name.get(event.style)
        if event.kind != "Dialogue" or not report or not is_dashes(report.role, style):
            continue
        if event.margins[0] or _PLACED_RE.search(event.text):
            continue
        plain = [p for p in re.sub(r"\{[^}]*\}", "", event.text).replace("\\n", "\\N").split("\\N") if p.strip()]
        if not plain:
            continue
        italic = house_fields(report.role, x, y, style)["italic"] == "-1"
        # Measured in vertical script units (the font size's), MarginL is horizontal.
        margin = (
            centring_margin(
                plain, style.font, style.size * y, italic, grid_width * y / x, style.margin_side * y, style.bold
            )
            * x
            / y
        )
        fields = dict(event.fields)
        fields["marginl"] = f"{round(margin):04d}"
        lines[event.line_index] = f"{event.kind}: " + ",".join(fields.values())
        count += 1
    return count
