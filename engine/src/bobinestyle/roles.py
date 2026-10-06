"""Which house style each style of a script should become.

Roles come from how a style is used, not from its name: fansubs and
streaming services name styles freely, and Crunchyroll even typesets signs
with ``Default`` plus inline tags. A line is plain dialogue unless its tags
position it, draw, karaoke or change its font; a style mostly made of plain
dialogue gets a dialogue role, refined by its look (top, italic, dashes,
overlap, wider margins). Anything else is typesetting and is left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from bobinestyle.ass import AssDocument, Event, Style


class Role(StrEnum):
    DIALOGUE = "dialogue"
    ITALIC = "italic"
    TOP = "top"
    TOP_ITALIC = "top_italic"
    DASHES = "dashes"
    DASHES_ITALIC = "dashes_italic"
    OVERLAP = "overlap"
    MARGINS = "margins"
    TYPESETTING = "typesetting"
    UNUSED = "unused"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    Role.DIALOGUE: "dialogue",
    Role.ITALIC: "italique",
    Role.TOP: "haut",
    Role.TOP_ITALIC: "haut italique",
    Role.DASHES: "tirets",
    Role.DASHES_ITALIC: "tirets italique",
    Role.OVERLAP: "overlap",
    Role.MARGINS: "marges",
    Role.TYPESETTING: "typo (inchangé)",
    Role.UNUSED: "inutilisé",
}

DIALOGUE_ROLES = frozenset(Role) - {Role.TYPESETTING, Role.UNUSED}

# Tags that make a line typesetting rather than dialogue.
_POSITIONED_RE = re.compile(r"\\(?:pos|move|org)\s*\(")
_TYPESET_RE = re.compile(r"\\(?:pos|move|org|clip|iclip)\s*\(|\\p[1-9]|\\(?:k|kf|ko|K)\d|\\fn|\\fs\d|\\fr[xyz]?-?\d")
_ALIGN_RE = re.compile(r"\\an([1-9])")
_ITALIC_RE = re.compile(r"\\i([01])(?!\d)")
_BLOCK_RE = re.compile(r"\{[^}]*\}")
_DASH_RE = re.compile(r"^\s*[-–—]")

# A style is dialogue when at least this share of its lines is...
DIALOGUE_SHARE = 0.5
# ...or when it carries a real part of the script's dialogue (Crunchyroll
# typesets signs with Default: an opening full of them can outnumber its
# lines in a short file). Never when its name says typesetting.
DIALOGUE_MIN_LINES = 3
DIALOGUE_MIN_SHARE_OF_SCRIPT = 0.1
_TYPESET_NAME_RE = re.compile(
    r"sign|panneau|\btit(?:le|re)|\bop\b|\bed\b|opening|ending|kara|song|chant|credit|générique|note|insert|logo",
    re.IGNORECASE,
)
# A secondary style whose lines mostly run over the main one's: overlap.
OVERLAP_SHARE = 0.6
# Extra side margin (in % of the script width) that marks a "margins" style.
MARGINS_EXTRA = 0.04


def is_positioned(event: Event) -> bool:
    return bool(_POSITIONED_RE.search(event.text))


def is_dialogue_line(event: Event) -> bool:
    return event.kind == "Dialogue" and not _TYPESET_RE.search(event.text)


def _leading_tags(text: str) -> str:
    match = re.match(r"^(?:\{[^}]*\})+", text)
    return match.group(0) if match else ""


def _plain(text: str) -> str:
    return _BLOCK_RE.sub("", text).replace("\\N", "\n").replace("\\n", "\n")


@dataclass
class StyleReport:
    style: Style
    role: Role
    lines: int = 0
    dialogue_lines: int = 0
    positioned_lines: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass
class ScriptReport:
    play_res: tuple[int, int] | None
    scaled_border_and_shadow: bool
    positioned_lines: int
    styles: list[StyleReport]

    @property
    def keep_play_res(self) -> bool:
        """Positioned lines are in PlayRes coordinates: changing PlayRes
        would move them."""
        return self.positioned_lines > 0

    @property
    def dialogue_lines(self) -> int:
        return sum(r.dialogue_lines for r in self.styles if r.role in DIALOGUE_ROLES)


def _majority(values: list, default):
    if not values:
        return default
    best = max(set(values), key=values.count)
    return best if values.count(best) * 2 > len(values) else default


def _effective_alignment(style: Style, lines: list[Event]) -> int:
    overrides = [int(m.group(1)) for e in lines if (m := _ALIGN_RE.search(_leading_tags(e.text)))]
    return _majority(overrides, style.alignment) if len(overrides) * 2 > len(lines) else style.alignment


def _effective_italic(style: Style, lines: list[Event]) -> bool:
    overrides = [m.group(1) == "1" for e in lines if (m := _ITALIC_RE.search(_leading_tags(e.text)))]
    return _majority(overrides, style.italic) if len(overrides) * 2 > len(lines) else style.italic


def _overlap_share(lines: list[Event], others: list[Event]) -> float:
    if not lines or not others:
        return 0.0
    spans = [(e.start, e.end) for e in others]
    hits = sum(any(s < e.end and e.start < t for s, t in spans) for e in lines)
    return hits / len(lines)


def analyze(doc: AssDocument) -> ScriptReport:
    by_style: dict[str, list[Event]] = {}
    for event in doc.events:
        if event.kind == "Dialogue":
            by_style.setdefault(event.style, []).append(event)

    reports: list[StyleReport] = []
    plain_by_style: dict[str, list[Event]] = {}
    for style in doc.styles:
        if doc.style(style.name) is not style:
            continue  # shadowed by a later style of the same name
        events = by_style.get(style.name, [])
        plain = [e for e in events if is_dialogue_line(e)]
        plain_by_style[style.name] = plain
        reports.append(StyleReport(style, Role.UNUSED, len(events), len(plain), sum(is_positioned(e) for e in events)))

    total_plain = sum(r.dialogue_lines for r in reports)
    dialogue: dict[str, list[Event]] = {}
    for report in reports:
        name, plain = report.style.name, plain_by_style[report.style.name]
        mostly = report.lines > 0 and len(plain) >= DIALOGUE_SHARE * report.lines
        carries = len(plain) >= max(DIALOGUE_MIN_LINES, DIALOGUE_MIN_SHARE_OF_SCRIPT * total_plain)
        if (mostly or carries) and not _TYPESET_NAME_RE.search(name):
            report.role = Role.DIALOGUE
            dialogue[name] = plain
            if not mostly:
                report.reasons.append(f"{report.lines - len(plain)} lignes de typo aussi")
        elif report.lines:
            report.role = Role.TYPESETTING
            report.reasons.append(f"{report.lines - len(plain)}/{report.lines} lignes de typo")

    if dialogue:
        # The main style is upright: italic ones keep their italic role.
        upright = [n for n in dialogue if not _effective_italic(doc.style(n), dialogue[n])] or list(dialogue)
        main_name = max(upright, key=lambda n: len(dialogue[n]))
        main_style = doc.style(main_name)
        width = (doc.play_res or (384, 288))[0]
        for report in reports:
            if report.role is not Role.DIALOGUE:
                continue
            lines = dialogue[report.style.name]
            if report.style.name == main_name:
                report.reasons.insert(0, "style principal")
            _refine(report, lines, main_style, dialogue[main_name], width)
    positioned = sum(is_positioned(e) for e in doc.events if e.kind == "Dialogue")
    return ScriptReport(doc.play_res, doc.scaled_border_and_shadow, positioned, reports)


def _refine(report: StyleReport, lines: list[Event], main: Style, main_lines: list[Event], width: int) -> None:
    style = report.style
    italic = _effective_italic(style, lines)
    alignment = _effective_alignment(style, lines)
    dashes = sum(bool(_DASH_RE.match(_plain(e.text))) for e in lines)
    is_main = style is main

    if alignment in (7, 8, 9):
        report.role = Role.TOP_ITALIC if italic else Role.TOP
        report.reasons.append(f"aligné en haut (\\an{alignment})")
    elif dashes * 2 > len(lines) and not is_main:
        report.role = Role.DASHES_ITALIC if italic else Role.DASHES
        report.reasons.append(f"{dashes}/{len(lines)} répliques à tirets")
    elif italic:
        report.role = Role.ITALIC
        report.reasons.append("italique")
    elif not is_main and (share := _overlap_share(lines, main_lines)) >= OVERLAP_SHARE:
        report.role = Role.OVERLAP
        report.reasons.append(f"{share:.0%} des lignes en même temps que le style principal")
    elif not is_main and _extra_margin(style, main) >= MARGINS_EXTRA * width:
        report.role = Role.MARGINS
        report.reasons.append("marges latérales plus larges")


def _extra_margin(style: Style, main: Style) -> float:
    (left, right, _), (main_left, main_right, _) = style.margins, main.margins
    return min(left - main_left, right - main_right)
