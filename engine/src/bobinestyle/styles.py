"""Subtitle styles: the house style, and the user's own.

A style's sizes are pixels of a 16:9 1080p screen (see ``scale``): each
video gets them at its own size. Its variants are the looks a dialogue
style can take by its role (see ``roles``) -- each one can be turned off,
the role then taking the plain dialogue's look.

The user's styles are kept in ``styles.json`` in the app's data folder
(BOBINESTYLE_DATA, given by the app); the house style is built in and
never stored.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class SubtitleStyle:
    name: str = "Style maison"
    # The dialogue.
    font: str = "Trebuchet MS"
    size: float = 66
    bold: bool = True
    italic: bool = False
    color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline: float = 2.5
    shadow_color: str = "#000000"
    shadow: float = 2.5
    margin_bottom: float = 75
    margin_side: float = 6
    # The variants, and what each changes.
    italic_variant: bool = True
    top_variant: bool = True
    top_margin: float = 75
    dashes_variant: bool = True
    overlap_variant: bool = True
    overlap_color: str = "#FAEE8C"
    margins_variant: bool = True
    margins_extra: float = 45

    def __post_init__(self) -> None:
        for name in ("color", "outline_color", "shadow_color", "overlap_color"):
            if not _COLOR_RE.match(getattr(self, name)):
                raise ValueError(f"{name}: not a #RRGGBB color: {getattr(self, name)!r}")
        if not self.name.strip() or not self.font.strip():
            raise ValueError("a style needs a name and a font")
        if not 1 <= self.size <= 400:
            raise ValueError(f"size out of range: {self.size}")
        for name in ("outline", "shadow", "margin_bottom", "margin_side", "top_margin", "margins_extra"):
            if not 0 <= getattr(self, name) <= 1000:
                raise ValueError(f"{name} out of range: {getattr(self, name)}")

    @classmethod
    def of(cls, data: dict) -> SubtitleStyle:
        """A style from its JSON, the fields it lacks the house style's."""
        known = {f.name for f in fields(cls)}
        return replace(HOUSE, **{k: v for k, v in data.items() if k in known})

    def to_json(self) -> dict:
        return asdict(self)


HOUSE = SubtitleStyle()


def ass_color(color: str) -> str:
    """ "#RRGGBB" as ASS's "&H00BBGGRR"."""
    r, g, b = color[1:3], color[3:5], color[5:7]
    return f"&H00{b}{g}{r}".upper()


# --- the user's styles ---------------------------------------------------------


def data_dir() -> Path:
    """Where the app keeps its data: the folder it gives (BOBINESTYLE_DATA),
    else the platform's usual one (the CLI, a test)."""
    given = os.environ.get("BOBINESTYLE_DATA")
    if given:
        return Path(given)
    base = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "com.bobinestyle.app"


def _styles_file() -> Path:
    return data_dir() / "styles.json"


def read_styles(path: Path | None = None) -> list[SubtitleStyle]:
    """The styles of ``path`` (the user's own when absent): none when the
    file isn't there. Raises ValueError on a file that isn't a styles file."""
    path = path or _styles_file()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [SubtitleStyle.of(item) for item in data["styles"]]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"{path.name}: {exc}") from exc


def write_styles(styles: list[SubtitleStyle], path: Path | None = None) -> None:
    """Writes ``styles`` to ``path`` (the user's own when absent), whole or
    not at all."""
    path = path or _styles_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_text(
        json.dumps({"styles": [s.to_json() for s in styles]}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(partial, path)
