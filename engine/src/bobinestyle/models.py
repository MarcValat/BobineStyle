from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StreamInfo:
    """One stream of a container, as ``ffmpeg -i`` reports it."""

    index: int
    kind: str  # "Video", "Audio", "Subtitle", "Attachment"...
    codec: str | None
    language: str | None
    title: str | None
    default: bool
    forced: bool
    # Video only: stored size and sample aspect ratio (1:1 = square pixels).
    width: int | None = None
    height: int | None = None
    sar: tuple[int, int] | None = None
    attached_pic: bool = False
    # Attachment only.
    filename: str | None = None

    @property
    def display_size(self) -> tuple[int, int] | None:
        """Size the picture is shown at: anamorphic pixels (DVD 720x576
        at SAR 64:45) are stretched horizontally (to 1024x576)."""
        if self.width is None or self.height is None:
            return None
        num, den = self.sar or (1, 1)
        if num <= 0 or den <= 0:
            return self.width, self.height
        return round(self.width * num / den), self.height


@dataclass(frozen=True)
class SubtitleStreamInfo:
    """A subtitle stream, ``index`` counting subtitle streams only (ffmpeg's
    ``0:s:N``), ``global_index`` counting all streams (``0:N``)."""

    index: int
    global_index: int
    codec: str
    language: str | None
    title: str | None
    default: bool
    forced: bool
