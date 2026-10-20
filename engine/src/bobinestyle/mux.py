"""Remux an MKV with its subtitles in the chosen languages in the house
style.

Their text tracks are restyled and named in their own language, full
("Français", "English") or forced ("Français (forcé)", "English
(forced)"); every other stream is copied untouched, in its original
order, with chapters and attachments. The fonts the restyled subtitles
use are attached when the MKV lacks them. The output is checked against
the source before it replaces its ``.part`` file; the source is never
modified.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from bobinestyle.ass import parse_ass
from bobinestyle.ffmpeg_backend import (
    TEXT_FORMATS,
    FFmpegError,
    container_duration,
    dump_attachments,
    extract_subtitle_text,
    ffmpeg_info,
    main_video,
    parse_streams,
    resolve_ffmpeg,
    run_checked,
    subtitle_streams,
)
from bobinestyle.fonts import MIMETYPES, FontFace, faces_for, font_faces, fonts_used, system_fonts
from bobinestyle.i18n import tr
from bobinestyle.languages import normalize, track_language, track_name
from bobinestyle.matroska import MatroskaError, cluster_timestamps, out_of_order
from bobinestyle.models import StreamInfo, SubtitleStreamInfo
from bobinestyle.srt import parse_srt, srt_to_ass
from bobinestyle.style import FONT, apply_house_style

_FORCED_TITLE_RE = re.compile(r"forc|sign|panneau", re.IGNORECASE)
# A track with less than this share of the fullest one's dialogue in its
# language only translates part of the film: it is the forced track.
FORCED_SHARE = 0.5

# What the subtitles are made for unless asked otherwise: French, the
# language the app was written for.
DEFAULT_LANGUAGES = ("fre",)
# Gaps tolerated between source and output durations, in seconds.
DURATION_TOLERANCE = 1.0


class MuxError(RuntimeError):
    """The remux failed or its output does not match the source."""


@dataclass
class TrackPlan:
    stream: SubtitleStreamInfo
    # Its language (normalized, guessed from its title when untagged), and
    # whether it's one of those chosen: restyled and named.
    language: str | None
    chosen: bool
    kind: str | None = None  # "full" or "forced" for chosen tracks
    text: str | None = None  # restyled ASS, None when the track is copied
    dialogue_lines: int | None = None
    title: str | None = None
    default: bool = False
    forced: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class MuxPlan:
    source: str
    video_size: tuple[int, int] | None
    streams: list[StreamInfo]
    tracks: list[TrackPlan]
    fonts: list[FontFace]
    fonts_present: list[str]
    fonts_missing: list[str]
    audio: StreamInfo | None = None
    warnings: list[str] = field(default_factory=list)
    # The language whose track becomes the default one.
    default_language: str | None = None

    @property
    def chosen(self) -> list[TrackPlan]:
        return [t for t in self.tracks if t.chosen]


def default_audio(streams: list[StreamInfo]) -> StreamInfo | None:
    """The audio track players start with: the first flagged default, else
    the first one."""
    audio = [s for s in streams if s.kind == "Audio"]
    return next((s for s in audio if s.default), audio[0] if audio else None)


def plan(path: str, languages: tuple[str, ...] = DEFAULT_LANGUAGES, default_language: str | None = None) -> MuxPlan:
    """What processing ``path`` does: its subtitles in ``languages``
    restyled and named, the default subtitle track ``default_language``'s
    (the first language's when not given), the fonts to attach."""
    chosen_languages = {normalize(code) for code in languages}
    default_language = (
        normalize(default_language) if default_language else normalize(languages[0]) if languages else None
    )
    info = ffmpeg_info(path)
    streams = parse_streams(info)
    video = main_video(streams)
    size = video.display_size if video else None
    subs = subtitle_streams(streams)
    # Untagged tracks whose title says nothing: the default language's, if
    # no other track is (as the old script took them as French).
    known = {track_language(s, None) for s in subs}
    fallback = default_language if default_language not in known else None
    tracks = []
    for s in subs:
        language = track_language(s, fallback)
        tracks.append(TrackPlan(s, language, language in chosen_languages))
    warnings: list[str] = []
    needed_fonts = {FONT.lower()}

    for track in tracks:
        if not track.chosen:
            continue
        fmt = TEXT_FORMATS.get(track.stream.codec)
        if fmt == "ass":
            result = apply_house_style(extract_subtitle_text(path, track.stream.index, track.stream.codec), size)
            track.text = result.text
            track.dialogue_lines = result.report.dialogue_lines
            track.notes += [tr("{name} : {label}", name=name, label=role.label) for name, role in result.restyled]
            track.notes += result.notes + result.warnings
            needed_fonts |= fonts_used(parse_ass(result.text))
        elif fmt == "srt":
            cues = parse_srt(extract_subtitle_text(path, track.stream.index, track.stream.codec))
            track.text = srt_to_ass(cues, size)
            track.dialogue_lines = len(cues)
        else:
            track.notes.append(tr("format image : copié tel quel"))

    chosen = [t for t in tracks if t.chosen]
    for language in {t.language for t in chosen}:
        same = [t for t in chosen if t.language == language]
        most = max((t.dialogue_lines or 0 for t in same), default=0)
        for track in same:
            s = track.stream
            few = track.dialogue_lines is not None and track.dialogue_lines < FORCED_SHARE * most
            track.kind = "forced" if s.forced or (s.title and _FORCED_TITLE_RE.search(s.title)) or few else "full"
        _name_tracks(same, language)
    audio = default_audio(streams)
    _pick_default(
        [t for t in chosen if t.language == default_language],
        audio_same=bool(audio and normalize(audio.language) == default_language),
    )
    if any(t.default for t in chosen):
        for track in tracks:
            if not track.chosen and track.stream.default:
                track.notes.append(tr("n'est plus la piste par défaut"))

    fonts, present, missing = _plan_fonts(path, needed_fonts) if any(t.text for t in chosen) else ([], [], [])
    if missing:
        warnings.append(tr("polices introuvables sur ce PC, non jointes : {fonts}", fonts=", ".join(sorted(missing))))
    return MuxPlan(path, size, streams, tracks, fonts, present, missing, audio, warnings, default_language)


def _name_tracks(same: list[TrackPlan], language: str | None) -> None:
    """One language's tracks: full ones named "Français", forced ones
    "Français (forcé)" and flagged forced -- in the language's own words.
    Same-kind tracks keep their old title to stay distinguishable."""
    for kind in ("full", "forced"):
        title = track_name(language or "und", kind == "forced")
        group = [t for t in same if t.kind == kind]
        for n, track in enumerate(group):
            track.title = title
            if n and track.stream.title:
                track.title = f"{title} – {track.stream.title}"
            elif n:
                track.title = f"{title} {n + 1}"
            track.forced = kind == "forced"
            track.default = False


def _pick_default(tracks: list[TrackPlan], audio_same: bool) -> None:
    """The default subtitle among the default language's ``tracks``
    follows the default audio: in that language, the forced track (only
    the foreign parts need translating); otherwise the full one (falling
    back on the other kind when one is missing)."""
    full = [t for t in tracks if t.kind == "full"]
    forced = [t for t in tracks if t.kind == "forced"]
    for track in forced[:1] if audio_same else (full or forced)[:1]:
        track.default = True


def _plan_fonts(path: str, needed: set[str]) -> tuple[list[FontFace], list[str], list[str]]:
    """Faces to attach, needed names already attached, names not found."""
    with tempfile.TemporaryDirectory(prefix="bobinestyle-") as tmp:
        attached = [f for p in dump_attachments(path, Path(tmp)) if (f := font_faces(p))]
    attached_families = {n for f in attached for n in f.families}
    attached_full = {n for f in attached for n in f.full_names}
    system = system_fonts()
    to_attach: list[FontFace] = []
    present: list[str] = []
    missing: list[str] = []
    for name in sorted(needed):
        faces = [f for f in faces_for(name, system) if not f.full_names & attached_full]
        if not faces:
            if name in attached_families or name in attached_full:
                present.append(name)
            elif not faces_for(name, system):
                missing.append(name)
            continue
        to_attach += [f for f in faces if f not in to_attach]
    return to_attach, present, missing


def default_output(source: str) -> Path:
    """``Output/<same name>.mkv`` next to the source, as the old script did."""
    path = Path(source)
    return path.parent / "Output" / path.name


def mux(p: MuxPlan, output: str | Path, progress: Callable[[float], None] | None = None) -> Path:
    """Write ``p.source`` remuxed to ``output``; ``progress`` hears how far
    the copy got (0 to 1)."""
    output = Path(output)
    if output.resolve() == Path(p.source).resolve():
        raise MuxError(tr("la sortie ne peut pas remplacer le fichier source"))
    output.parent.mkdir(parents=True, exist_ok=True)
    by_global = {t.stream.global_index: t for t in p.tracks}

    inputs: list[str] = ["-i", p.source]
    input_count = 1
    maps: list[str] = []
    tags: list[str] = []
    partial = output.with_name(f"{output.stem}.part{output.suffix}")
    try:
        with tempfile.TemporaryDirectory(prefix="bobinestyle-") as tmp:
            for stream in p.streams:
                position = len(maps) // 2
                track = by_global.get(stream.index)
                if track and track.text is not None:
                    restyled = Path(tmp) / f"track{track.stream.index}.ass"
                    restyled.write_text(track.text, encoding="utf-8")
                    inputs += ["-i", str(restyled)]
                    maps += ["-map", f"{input_count}:0"]
                    input_count += 1
                else:
                    maps += ["-map", f"0:{stream.index}"]
                if track and track.chosen:
                    tags += [
                        f"-metadata:s:{position}",
                        f"language={track.language}",
                        f"-metadata:s:{position}",
                        f"title={track.title}",
                    ]
                    flags = [f for f, on in (("default", track.default), ("forced", track.forced)) if on]
                    tags += [f"-disposition:{position}", "+".join(flags) or "0"]
                elif track and track.stream.default and any(t.default for t in p.chosen):
                    tags += [f"-disposition:{position}", "forced" if stream.forced else "0"]

            names = {s.filename for s in p.streams if s.filename}
            attach: list[str] = []
            for n, face in enumerate(p.fonts):
                position = len(maps) // 2 + n
                filename = _unique(face.path.name, names)
                attach += ["-attach", str(face.path)]
                tags += [
                    f"-metadata:s:{position}",
                    f"mimetype={MIMETYPES[face.path.suffix.lower()]}",
                    f"-metadata:s:{position}",
                    f"filename={filename}",
                ]
            # -copyts: the restyled ASS were extracted with the container's
            # timestamps; without it ffmpeg would move the MKV by minus its
            # start time (AAC priming, B-frames) but not the standalone ASS.
            run_checked(
                [
                    resolve_ffmpeg(),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-copyts",
                    *inputs,
                    *maps,
                    *attach,
                    "-map_metadata",
                    "0",
                    "-map_chapters",
                    "0",
                    "-metadata",
                    "title=",
                    # Strict time order: by default ffmpeg stops waiting
                    # for a stream once others are 10 s ahead, and the
                    # sparse subtitles read from their own files then land
                    # in clusters out of order (one at 3:19 before one at
                    # 0:14). VLC skips those blocks: the lines never show.
                    "-max_interleave_delta",
                    "0",
                    *tags,
                    "-c",
                    "copy",
                    "-f",
                    "matroska",
                    str(partial),
                ],
                on_size=_progress_reporter(p.source, progress),
            )
        verify(p, str(partial))
        os.replace(partial, output)
    except FFmpegError as exc:
        raise MuxError(str(exc)) from exc
    finally:
        partial.unlink(missing_ok=True)
    return output


def _progress_reporter(source: str, progress: Callable[[float], None] | None) -> Callable[[int], None] | None:
    """Bytes written as a share of the source: a remux copies it whole (the
    fonts added are a rounding error)."""
    size = Path(source).stat().st_size if progress else 0
    if not progress or not size:
        return None
    return lambda written: progress(min(written / size, 1.0))


def _unique(name: str, taken: set[str]) -> str:
    stem, suffix = os.path.splitext(name)
    candidate, n = name, 1
    while candidate.lower() in {t.lower() for t in taken}:
        candidate = f"{stem}_{n}{suffix}"
        n += 1
    taken.add(candidate)
    return candidate


def verify(p: MuxPlan, output: str) -> None:
    """The output has every source stream, in order and with the same
    codec, plus the new fonts; same duration; Dolby Vision kept; its
    clusters in time order."""
    source_info, output_info = ffmpeg_info(p.source), ffmpeg_info(output)
    converted = {t.stream.global_index for t in p.tracks if t.text is not None}
    source, result = p.streams, parse_streams(output_info)
    expected = [(s.kind, "ass" if s.index in converted else s.codec) for s in source]
    expected += [("Attachment", None)] * len(p.fonts)
    got = [(s.kind, s.codec) for s in result]
    if len(got) != len(expected):
        raise MuxError(tr("{got} flux dans la sortie au lieu de {expected}", got=len(got), expected=len(expected)))
    for n, ((kind, codec), (got_kind, got_codec)) in enumerate(zip(expected, got)):
        if kind != got_kind or (kind != "Attachment" and codec != got_codec):
            raise MuxError(
                tr(
                    "flux {n} : {kind} {codec} devenu {got_kind} {got_codec}",
                    n=n,
                    kind=kind,
                    codec=codec,
                    got_kind=got_kind,
                    got_codec=got_codec,
                )
            )
    before, after = container_duration(source_info), container_duration(output_info)
    if before is not None and (after is None or abs(before - after) > DURATION_TOLERANCE):
        raise MuxError(tr("durée {after} s au lieu de {before} s", after=after, before=before))
    if source_info.count("DOVI configuration") != output_info.count("DOVI configuration"):
        raise MuxError(tr("les métadonnées Dolby Vision ont été perdues"))
    # Clusters in time order: VLC skips the blocks of one written too early
    # (subtitles that never show), however well ffmpeg itself reads it.
    try:
        backwards = out_of_order(cluster_timestamps(output))
    except (MatroskaError, OSError) as exc:
        raise MuxError(tr("fichier écrit illisible : {error}", error=exc)) from exc
    if backwards:
        raise MuxError(
            tr(
                "{count} groupe(s) de blocs hors de l'ordre du temps : certains lecteurs n'afficheraient pas tout",
                count=backwards,
            )
        )
