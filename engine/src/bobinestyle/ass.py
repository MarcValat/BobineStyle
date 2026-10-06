"""Read an ASS (or SSA) script without losing anything.

The script is kept as its original lines; parsed sections point back into
them so later edits can rewrite only the lines they change (styles, a few
[Script Info] keys) and leave every event untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# SSA's [V4 Styles] numbers alignments differently: 1-3 bottom, 5-7 top,
# 9-11 middle. Mapped to the numpad layout of ASS (\an).
_SSA_ALIGNMENT = {1: 1, 2: 2, 3: 3, 5: 7, 6: 8, 7: 9, 9: 4, 10: 5, 11: 6}

_TIME_RE = re.compile(r"^(\d+):(\d{1,2}):(\d{1,2})(?:[.,](\d+))?$")


def parse_time(value: str) -> float:
    """``H:MM:SS.cc`` to seconds (0 for anything malformed)."""
    match = _TIME_RE.match(value.strip())
    if not match:
        return 0.0
    h, m, s, frac = match.groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + (int(frac) / 10 ** len(frac) if frac else 0.0)


def parse_color(value: str) -> tuple[int, int, int, int]:
    """``&HAABBGGRR`` (or a decimal number, as SSA writes) to (r, g, b, alpha)."""
    value = value.strip().rstrip("&")
    try:
        number = int(value[2:], 16) if value[:2].upper() == "&H" else int(value)
    except ValueError:
        return 255, 255, 255, 0
    return number & 0xFF, (number >> 8) & 0xFF, (number >> 16) & 0xFF, (number >> 24) & 0xFF


def _number(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


@dataclass
class Style:
    line_index: int
    fields: dict[str, str]  # Format name (lowercase) -> raw value
    ssa: bool = False

    @property
    def name(self) -> str:
        return self.fields.get("name", "").strip()

    @property
    def fontname(self) -> str:
        return self.fields.get("fontname", "").strip()

    @property
    def fontsize(self) -> float:
        return _number(self.fields.get("fontsize"), 20)

    @property
    def bold(self) -> bool:
        return _number(self.fields.get("bold")) != 0

    @property
    def italic(self) -> bool:
        return _number(self.fields.get("italic")) != 0

    @property
    def alignment(self) -> int:
        value = int(_number(self.fields.get("alignment"), 2))
        return _SSA_ALIGNMENT.get(value, 2) if self.ssa else value

    @property
    def outline(self) -> float:
        return _number(self.fields.get("outline"))

    @property
    def shadow(self) -> float:
        return _number(self.fields.get("shadow"))

    @property
    def primary_color(self) -> tuple[int, int, int, int]:
        return parse_color(self.fields.get("primarycolour", "&H00FFFFFF"))

    @property
    def margins(self) -> tuple[int, int, int]:
        return tuple(int(_number(self.fields.get(k))) for k in ("marginl", "marginr", "marginv"))


@dataclass
class Event:
    line_index: int
    kind: str  # "Dialogue" or "Comment"
    fields: dict[str, str]

    @property
    def style(self) -> str:
        return self.fields.get("style", "").strip().lstrip("*")

    @property
    def actor(self) -> str:
        return self.fields.get("name", "").strip()

    @property
    def text(self) -> str:
        return self.fields.get("text", "")

    @property
    def start(self) -> float:
        return parse_time(self.fields.get("start", ""))

    @property
    def end(self) -> float:
        return parse_time(self.fields.get("end", ""))

    @property
    def margins(self) -> tuple[int, int, int]:
        return tuple(int(_number(self.fields.get(k))) for k in ("marginl", "marginr", "marginv"))


@dataclass
class AssDocument:
    lines: list[str]
    info: dict[str, str] = field(default_factory=dict)  # [Script Info], key as written
    styles: list[Style] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    def info_value(self, key: str) -> str | None:
        """A [Script Info] value, the key matched case-insensitively."""
        key = key.lower()
        return next((v for k, v in self.info.items() if k.lower() == key), None)

    @property
    def play_res(self) -> tuple[int, int] | None:
        """PlayResX/Y as the renderer resolves them: a missing one is derived
        from the other (4:3), both missing mean None (renderers use 384x288)."""
        x, y = (_number(self.info_value(k), 0) for k in ("PlayResX", "PlayResY"))
        x, y = int(x), int(y)
        if x <= 0 and y <= 0:
            return None
        if x <= 0:
            x = 1280 if y == 1024 else round(y * 4 / 3)
        if y <= 0:
            y = 1024 if x == 1280 else round(x * 3 / 4)
        return x, y

    @property
    def scaled_border_and_shadow(self) -> bool:
        return (self.info_value("ScaledBorderAndShadow") or "").strip().lower() == "yes"

    def style(self, name: str) -> Style | None:
        """The style a renderer uses for ``name``: the last of that name."""
        return next((s for s in reversed(self.styles) if s.name == name), None)


def _split_fields(value: str, names: list[str]) -> dict[str, str]:
    parts = value.split(",", len(names) - 1)
    parts += [""] * (len(names) - len(parts))
    return dict(zip(names, parts))


def parse_ass(text: str) -> AssDocument:
    text = text.removeprefix("﻿")
    doc = AssDocument(lines=text.splitlines())
    section = ""
    formats: dict[str, list[str]] = {}
    for i, raw in enumerate(doc.lines):
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.lower()
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.lstrip()
        if section == "[script info]":
            doc.info.setdefault(key, value.strip())
        elif section in ("[v4+ styles]", "[v4 styles]", "[v4 styles+]"):
            if key.lower() == "format":
                formats[section] = [n.strip().lower() for n in value.split(",")]
            elif key.lower() == "style":
                names = formats.get(section) or _DEFAULT_STYLE_FORMAT
                doc.styles.append(Style(i, _split_fields(value, names), ssa=section == "[v4 styles]"))
        elif section == "[events]":
            if key.lower() == "format":
                formats[section] = [n.strip().lower() for n in value.split(",")]
            elif key in ("Dialogue", "Comment"):
                names = formats.get(section) or _DEFAULT_EVENT_FORMAT
                doc.events.append(Event(i, key, _split_fields(value, names)))
    return doc


_DEFAULT_STYLE_FORMAT = [
    n.lower()
    for n in (
        "Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,"
        "StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding"
    ).split(",")
]
_DEFAULT_EVENT_FORMAT = "layer,start,end,style,name,marginl,marginr,marginv,effect,text".split(",")
