"""Messages the user reads (plan notes, warnings, job logs, errors), in the
GUI's language. From Bobine Audio.

A message is written in French, as a ``str.format`` template, and passed
through ``tr``: in French (the default, and the CLI's language) it comes
out as written; in English, its translation from ``_EN`` does. The GUI
sets the language (``POST /language``) at startup and whenever it changes.
A test checks that every template in the code has its translation.
"""

from __future__ import annotations

LANGUAGES = ("fr", "en")

_language = "fr"


def set_language(language: str) -> None:
    global _language
    if language not in LANGUAGES:
        raise ValueError(f"Unknown language: {language!r}")
    _language = language


def get_language() -> str:
    return _language


def tr(template: str, /, **values: object) -> str:
    """``template`` in the current language, filled with ``values``."""
    text = _EN.get(template, template) if _language == "en" else template
    return text.format(**values)


_EN: dict[str, str] = {
    # roles (a style's role, roles._LABELS)
    "dialogue": "dialogue",
    "italique": "italic",
    "haut": "top",
    "haut italique": "top italic",
    "tirets": "dashes",
    "tirets italique": "dashes italic",
    "overlap": "overlap",
    "marges": "margins",
    "typo (inchangé)": "typesetting (unchanged)",
    "inutilisé": "unused",
    # style
    "PlayRes {old_width}x{old_height} n'a pas les proportions de la vidéo ({width}x{height}) : "
    "le texte peut être déformé, PlayRes conservé à cause du positionnement": "PlayRes {old_width}x{old_height} doesn't have "
    "the video's proportions ({width}x{height}): the text may be distorted, PlayRes kept because of the positioning",
    "ScaledBorderAndShadow passe à yes : les contours et ombres fixés dans les lignes changent d'épaisseur": "ScaledBorderAndShadow "
    "set to yes: the outlines and shadows set in the lines change thickness",
    "aucun style de dialogue : seuls les en-têtes ont été modifiés": "no dialogue style: only the headers were changed",
    "{count} réplique(s) à tirets centrée(s) par leur marge": "{count} dash line(s) centered by their margin",
    # mux
    "{name} : {label}": "{name}: {label}",
    "SRT converti en ASS": "SRT converted to ASS",
    "format image : copié tel quel": "image format: copied as is",
    "n'est plus la piste par défaut": "no longer the default track",
    "polices introuvables sur ce PC, non jointes : {fonts}": "fonts not found on this PC, not attached: {fonts}",
    "la sortie ne peut pas remplacer le fichier source": "the output can't replace the source file",
    "{got} flux dans la sortie au lieu de {expected}": "{got} streams in the output instead of {expected}",
    "flux {n} : {kind} {codec} devenu {got_kind} {got_codec}": "stream {n}: {kind} {codec} became {got_kind} {got_codec}",
    "durée {after} s au lieu de {before} s": "duration {after} s instead of {before} s",
    "les métadonnées Dolby Vision ont été perdues": "the Dolby Vision metadata was lost",
    "fichier écrit illisible : {error}": "written file unreadable: {error}",
    "{count} groupe(s) de blocs hors de l'ordre du temps : certains lecteurs n'afficheraient pas tout": "{count} block "
    "group(s) out of time order: some players wouldn't show everything",
    # server
    "Fichier introuvable : {path}": "File not found: {path}",
    "Analyse des pistes…": "Reading the tracks…",
    "aucune piste de sous-titres française": "no French subtitle track",
    "Remux…": "Remuxing…",
    "Écrit et vérifié : {path}": "Written and checked: {path}",
    "Tâche inconnue : {job_id}": "Unknown task: {job_id}",
    # ffmpeg_backend
    "ffmpeg introuvable : ni sur le PATH, ni via le paquet imageio-ffmpeg.": "ffmpeg not found: neither on the PATH nor "
    "through the imageio-ffmpeg package.",
    "Échec de ffmpeg :\n{command}\n{details}": "ffmpeg failed:\n{command}\n{details}",
    "Fichier introuvable : {path!r}": "File not found: {path!r}",
    "Impossible de lire {path!r} :\n{details}": "Can't read {path!r}:\n{details}",
    "Format de sous-titres non pris en charge : {codec}": "Unsupported subtitle format: {codec}",
    "Impossible d'extraire la piste de sous-titres {track} :\n{details}": "Can't extract subtitle track {track}:\n{details}",
}
