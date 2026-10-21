"""Subtitle languages: one code per language, a track's language when its
tag is missing, and the names tracks get in their own language.

Matroska tags languages in ISO 639-2, some files in its "terminology"
codes (fra, deu) or in ISO 639-1 (fr, de): all come down to the
"bibliographic" one Matroska prefers (fre, ger). A track named in its
own language ("Français", "English (forced)") reads the same whatever
the player's language.
"""

from __future__ import annotations

import re

from bobinestyle.models import SubtitleStreamInfo

# Other spellings of a language, to its Matroska code.
_ALIASES = {
    "fra": "fre",
    "fr": "fre",
    "en": "eng",
    "deu": "ger",
    "de": "ger",
    "es": "spa",
    "it": "ita",
    "pt": "por",
    "nld": "dut",
    "nl": "dut",
    "pl": "pol",
    "ru": "rus",
    "ja": "jpn",
    "zho": "chi",
    "zh": "chi",
    "ko": "kor",
    "sv": "swe",
    "da": "dan",
    "fi": "fin",
    "no": "nor",
    "nb": "nor",
    "tr": "tur",
    "ar": "ara",
}

# Each language's name in itself, full and forced. A language not here
# keeps its code.
TRACK_NAMES: dict[str, tuple[str, str]] = {
    "fre": ("Français", "Français (forcé)"),
    "eng": ("English", "English (forced)"),
    "ger": ("Deutsch", "Deutsch (erzwungen)"),
    "spa": ("Español", "Español (forzados)"),
    "ita": ("Italiano", "Italiano (forzati)"),
    "por": ("Português", "Português (forçadas)"),
    "dut": ("Nederlands", "Nederlands (geforceerd)"),
    "pol": ("Polski", "Polski (wymuszone)"),
    "jpn": ("日本語", "日本語 (強制)"),
}

# What a track's title says of its language, when its tag doesn't.
_TITLE_HINTS = {
    "fre": re.compile(r"fran[cç]|french|\bvf|vostfr", re.IGNORECASE),
    "eng": re.compile(r"english|\beng\b|anglais", re.IGNORECASE),
    "ger": re.compile(r"deutsch|german|allemand", re.IGNORECASE),
    "spa": re.compile(r"espa[nñ]ol|spanish|castellano|latino|espagnol", re.IGNORECASE),
    "ita": re.compile(r"italian|italien", re.IGNORECASE),
    "por": re.compile(r"portugu", re.IGNORECASE),
}


def normalize(code: str | None) -> str | None:
    """``code`` as Matroska's bibliographic ISO 639-2 code ("fra" -> "fre")."""
    if not code:
        return None
    code = code.lower()
    return _ALIASES.get(code, code)


def track_language(stream: SubtitleStreamInfo, fallback: str | None) -> str | None:
    """A subtitle track's language: its tag, else what its title says, else
    ``fallback`` (a file's only untagged tracks are taken as that one, as
    the old script took them as French)."""
    tagged = normalize(stream.language)
    if tagged:
        return tagged
    for code, hint in _TITLE_HINTS.items():
        if stream.title and hint.search(stream.title):
            return code
    return fallback


def track_name(language: str, forced: bool) -> str:
    """A track's name in its own language: "English", "English (forced)"."""
    names = TRACK_NAMES.get(language)
    if names is None:
        return f"{language} (forced)" if forced else language
    return names[1] if forced else names[0]
