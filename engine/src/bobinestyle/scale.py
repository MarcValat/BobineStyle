"""How big the house style is drawn on a given video.

The house style is defined in pixels of a 16:9 1080p screen. A video is
shown fitted into that screen, so a value measured on the screen becomes
``value * k`` in the video's own pixels, ``k`` being how much the video is
shrunk to fit. Scope (1920x800) and 4:3 (1440x1080) films thus keep the same
on-screen text size as a 16:9 one.
"""

from __future__ import annotations

REFERENCE_SCREEN = (1920, 1080)


def screen_scale(display_width: int, display_height: int) -> float:
    """Factor from reference-screen pixels to the video's display pixels."""
    ref_w, ref_h = REFERENCE_SCREEN
    return max(display_width / ref_w, display_height / ref_h)
