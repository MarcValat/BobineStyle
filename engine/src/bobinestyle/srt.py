"""Convert an SRT into an ASS script in the house style.

Each cue gets the house style matching its content: fully italic cues
"Italique", cues tagged {\\an8} the top styles, two-speaker dash cues the
dash styles (left-aligned block, centred by its own margin as Crunchyroll
does), cues shown over another one "Overlap". HTML tags become ASS tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bobinestyle.measure import centring_margin
from bobinestyle.roles import Role
from bobinestyle.scale import screen_scale
from bobinestyle.style import FONT, FONT_SIZE, MARGIN_SIDE, house_fields

_TIME = r"(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})"
_TIMING_RE = re.compile(_TIME + r"\s*-->\s*" + _TIME)
_BLANK_LINES_RE = re.compile(r"\n[ \t]*\n")
_TAG_RE = re.compile(r"<\s*(/?)\s*([a-z]+)([^>]*)>", re.IGNORECASE)
_COLOR_RE = re.compile(r"color\s*=\s*[\"']?#?([0-9a-f]{6})", re.IGNORECASE)
_ASS_BLOCK_RE = re.compile(r"\{[^}]*\}")
_AN_RE = re.compile(r"\{\\an([1-9])\}")
_DASH_RE = re.compile(r"^\s*[-–—]")

# A cue is an overlap when it runs over the previous one for this long (or
# half its own duration): shorter overlaps are timing slop.
OVERLAP_MIN_S = 0.5

STYLE_NAMES = {
    Role.DIALOGUE: "Default",
    Role.ITALIC: "Italique",
    Role.TOP: "DefaultTop",
    Role.TOP_ITALIC: "ItaliqueTop",
    Role.DASHES: "TiretsDefault",
    Role.DASHES_ITALIC: "TiretsItalique",
    Role.OVERLAP: "Overlap",
}

STYLE_FORMAT = (
    "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
    "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
    "MarginL, MarginR, MarginV, Encoding"
)


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str  # SRT text, lines joined by "\n"


def parse_srt(text: str) -> list[Cue]:
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    cues: list[Cue] = []
    for block in _BLANK_LINES_RE.split(text.strip()):
        lines = block.split("\n")
        at = next((i for i, line in enumerate(lines) if _TIMING_RE.search(line)), None)
        if at is None:
            # A stray blank line inside a cue split it: the rest belongs to it.
            if cues and block.strip():
                prev = cues[-1]
                cues[-1] = Cue(prev.start, prev.end, prev.text + "\n" + block.strip("\n"))
            continue
        g = _TIMING_RE.search(lines[at]).groups()
        start = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 10 ** len(g[3])
        end = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 10 ** len(g[7])
        body = "\n".join(lines[at + 1 :]).strip("\n")
        if body.strip():
            cues.append(Cue(start, end, body))
    return cues


def html_to_ass(text: str) -> str:
    """SRT markup to ASS override tags, lines joined by \\N."""

    def tag(match: re.Match) -> str:
        closing, name, attrs = match.group(1), match.group(2).lower(), match.group(3)
        if name in ("i", "b", "u", "s"):
            return f"{{\\{name}{0 if closing else 1}}}"
        if name == "font":
            if closing:
                return "{\\c}"
            if color := _COLOR_RE.search(attrs):
                rgb = color.group(1).upper()
                return f"{{\\c&H{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}&}}"  # ASS colours are BGR
        return ""

    return _TAG_RE.sub(tag, text).replace("\n", "\\N")


def _plain_lines(ass_text: str) -> list[str]:
    return _ASS_BLOCK_RE.sub("", ass_text).split("\\N")


def _fully_italic(ass_text: str) -> bool:
    """Every visible character is inside {\\i1}...{\\i0}."""
    italic, seen = False, False
    for part in re.split(r"(\{[^}]*\})", ass_text):
        if part.startswith("{"):
            for value in re.findall(r"\\i([01])(?!\d)", part):
                italic = value == "1"
        elif part.replace("\\N", "").strip():
            if not italic:
                return False
            seen = True
    return seen


def _strip_italic(ass_text: str) -> str:
    text = re.sub(r"\\i[01](?!\d)", "", ass_text)
    return text.replace("{}", "")


def _ass_time(t: float) -> str:
    cs = round(max(t, 0.0) * 100)
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


@dataclass
class _Line:
    cue: Cue
    text: str
    role: Role
    margin_l: int = 0


def _classify(cues: list[Cue]) -> list[_Line]:
    lines: list[_Line] = []
    for n, cue in enumerate(cues):
        text = html_to_ass(cue.text)
        top = False
        if (an := _AN_RE.search(text)) and an.group(1) in "789":
            top = an.group(1) == "8"
            if top:
                text = _AN_RE.sub("", text, count=1)
        italic = _fully_italic(text)
        if italic:
            text = _strip_italic(text)
        plain = _plain_lines(text)
        dashes = len(plain) >= 2 and all(_DASH_RE.match(line) for line in plain if line.strip())
        previous = cues[n - 1] if n else None
        overlap = previous is not None and min(previous.end, cue.end) - cue.start >= min(
            OVERLAP_MIN_S, (cue.end - cue.start) / 2
        )
        if top:
            role = Role.TOP_ITALIC if italic else Role.TOP
        elif dashes:
            role = Role.DASHES_ITALIC if italic else Role.DASHES
        elif overlap and not italic:
            role = Role.OVERLAP
        else:
            role = Role.ITALIC if italic else Role.DIALOGUE
        lines.append(_Line(cue, text, role))
    return lines


def srt_to_ass(cues: list[Cue], video_size: tuple[int, int] | None) -> str:
    """``cues`` (from ``parse_srt``) as an ASS script for a video shown at
    ``video_size``."""
    width, height = video_size or (1920, 1080)
    k = screen_scale(width, height)
    lines = _classify(cues)

    size = FONT_SIZE * k
    for line in lines:
        if line.role in (Role.DASHES, Role.DASHES_ITALIC):
            italic = line.role is Role.DASHES_ITALIC
            line.margin_l = centring_margin(_plain_lines(line.text), FONT, size, italic, width, MARGIN_SIDE * k)

    used = [Role.DIALOGUE] + [r for r in STYLE_NAMES if r is not Role.DIALOGUE and any(l.role is r for l in lines)]
    styles = []
    for role in used:
        fields = house_fields(role, k, k)
        styles.append(
            "Style: " + ",".join([STYLE_NAMES[role]] + [fields[name] for name in _style_field_names()[1:]])
        )
    events = [
        f"Dialogue: 0,{_ass_time(l.cue.start)},{_ass_time(l.cue.end)},{STYLE_NAMES[l.role]},,"
        f"{l.margin_l:04d},0000,0000,,{l.text}"
        for l in lines
    ]
    return "\n".join(
        [
            "[Script Info]",
            "; Converted from SRT by Bobine Style",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            # No colour-matrix conversion: white stays white whatever the video.
            "YCbCr Matrix: None",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "",
            "[V4+ Styles]",
            f"Format: {STYLE_FORMAT}",
            *styles,
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            *events,
            "",
        ]
    )


def _style_field_names() -> list[str]:
    return [n.strip().lower() for n in STYLE_FORMAT.split(",")]
