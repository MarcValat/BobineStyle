"""End-to-end: real MKV files through ffmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bobinestyle.ass import parse_ass
from bobinestyle.ffmpeg_backend import extract_subtitle_text, probe_streams, resolve_ffmpeg, subtitle_streams
from bobinestyle.fonts import faces_for, system_fonts
from bobinestyle.models import SubtitleStreamInfo
from bobinestyle.models import StreamInfo
from bobinestyle.mux import (
    FORCED_TITLE,
    FULL_TITLE,
    MuxError,
    TrackPlan,
    _is_french,
    _name_tracks,
    default_audio,
    mux,
    plan,
    verify,
)
from test_roles import _line, _script, _style

FULL = _script(
    [_style("Default"), _style("Italique", italic=1)],
    [_line(t, "Default", f"Réplique {t}") for t in range(10, 40, 3)] + [_line(41, "Italique", "Pensée")],
    info="PlayResX: 640\nPlayResY: 360\n",
)
SIGNS = _script(
    [_style("Default")],
    [_line(12, "Default", "{\\fnImpact\\pos(320,100)}PANNEAU", "Sign")],
    info="PlayResX: 640\nPlayResY: 360\n",
)
ENGLISH = "1\n00:00:10,000 --> 00:00:12,000\nHello\n"


def _ff(*args: str) -> None:
    subprocess.run([resolve_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def _pts_ms(path: Path, selector: str) -> list[int]:
    out = subprocess.run(
        [resolve_ffmpeg(), "-hide_banner", "-loglevel", "error", "-copyts", "-i", str(path),
         "-map", selector, "-c", "copy", "-f", "framecrc", "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [int(line.split(",")[2]) for line in out.splitlines() if not line.startswith("#")]


@pytest.fixture(params=["negative_start", "positive_start"])
def mkv(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """Video, English SRT (default), French full and signs ASS; the file
    starting below 0 (AAC priming) or above it (delayed video)."""
    (tmp_path / "en.srt").write_text(ENGLISH, encoding="utf-8")
    (tmp_path / "full.ass").write_text(FULL, encoding="utf-8")
    (tmp_path / "signs.ass").write_text(SIGNS, encoding="utf-8")
    subs = ["-i", str(tmp_path / "en.srt"), "-i", str(tmp_path / "full.ass"), "-i", str(tmp_path / "signs.ass")]
    tags = [
        "-metadata:s:s:0", "language=eng", "-disposition:s:0", "default",
        "-metadata:s:s:1", "language=fre", "-metadata:s:s:1", "title=French",
        "-metadata:s:s:2", "language=fre", "-metadata:s:s:2", "title=French Signs",
    ]
    video = ["-f", "lavfi", "-i", "color=c=black:s=128x72:r=5:d=45"]
    out = tmp_path / "in.mkv"
    if request.param == "negative_start":
        _ff(*video, "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono", *subs,
            "-map", "0", "-map", "1", "-map", "2", "-map", "3", "-map", "4", "-t", "45",
            "-c:v", "mpeg4", "-c:a", "aac", "-c:s", "copy", *tags, str(out))
    else:
        _ff("-copyts", "-itsoffset", "0.25", *video, *subs,
            "-map", "0", "-map", "1", "-map", "2", "-map", "3", "-t", "45",
            "-c:v", "mpeg4", "-c:s", "copy", *tags, str(out))
    return out


def test_plan_labels_french_tracks(mkv: Path):
    p = plan(str(mkv))
    english, full, signs = p.tracks
    assert not english.french
    # No French audio: the full track is the default one.
    assert (full.kind, full.title, full.default, full.forced) == ("full", FULL_TITLE, True, False)
    assert (signs.kind, signs.title, signs.default, signs.forced) == ("forced", FORCED_TITLE, False, True)
    assert "impact" in {n for f in p.fonts for n in f.families} or "impact" in p.fonts_missing


def test_mux_restyles_keeps_timing_and_attaches_fonts(mkv: Path, tmp_path: Path):
    p = plan(str(mkv))
    out = mux(p, tmp_path / "out" / "result.mkv")
    assert not (tmp_path / "out" / "result.part.mkv").exists()

    subs = subtitle_streams(probe_streams(str(out)))
    assert [(s.language, s.title, s.default, s.forced) for s in subs] == [
        ("eng", None, False, False),  # no longer default: a French track is
        ("fre", FULL_TITLE, True, False),
        ("fre", FORCED_TITLE, False, True),
    ]
    restyled = parse_ass(extract_subtitle_text(str(out), 1, "ass"))
    assert restyled.style("Default").fontname == "Trebuchet MS"
    # Unpinned script on a 128x72 video: PlayRes 128x72, 66 * 72 / 1080.
    assert restyled.play_res == (128, 72)
    assert restyled.style("Default").fields["fontsize"] == "4.4"
    # Same place against the video as in the source, whatever its start.
    # (ffmpeg may move the whole file to start at 0: compare against the video.)
    for selector in ("0:s:0", "0:s:1", "0:s:2"):
        before = [t - _pts_ms(mkv, "0:v:0")[0] for t in _pts_ms(mkv, selector)]
        after = [t - _pts_ms(out, "0:v:0")[0] for t in _pts_ms(out, selector)]
        assert after == before, selector

    attached = {s.filename for s in probe_streams(str(out)) if s.kind == "Attachment"}
    assert attached == {f.path.name for f in p.fonts}
    if faces_for("trebuchet ms", system_fonts()):
        assert "trebuc.ttf" in {name.lower() for name in attached}


def test_fonts_already_attached_are_not_added_twice(mkv: Path, tmp_path: Path):
    first = mux(plan(str(mkv)), tmp_path / "first.mkv")
    again = plan(str(first))
    assert again.fonts == []
    assert "trebuchet ms" in again.fonts_present or "trebuchet ms" in again.fonts_missing


def test_verify_rejects_a_mismatch(mkv: Path, tmp_path: Path):
    p = plan(str(mkv))
    out = mux(p, tmp_path / "out.mkv")
    p.streams = p.streams[:-1]  # one stream fewer than the output has
    with pytest.raises(MuxError):
        verify(p, str(out))


def test_source_is_never_overwritten(mkv: Path):
    with pytest.raises(MuxError):
        mux(plan(str(mkv)), mkv)


def _sub(language: str | None, title: str | None = None) -> SubtitleStreamInfo:
    return SubtitleStreamInfo(0, 0, "ass", language, title, False, False)


def test_french_detection():
    assert _is_french(_sub("fre"), True)
    assert not _is_french(_sub("eng"), False)
    assert _is_french(_sub(None, "VF"), True)
    assert not _is_french(_sub(None), True)  # undetermined beside a real French track
    assert _is_french(_sub(None), False)  # the only candidate, as the old script assumed



def _tracks(*kinds: str) -> list[TrackPlan]:
    tracks = [TrackPlan(_sub("fre"), True) for _ in kinds]
    for track, kind in zip(tracks, kinds):
        track.kind = kind
    return tracks


def _defaults(tracks: list[TrackPlan]) -> list[tuple[str, bool, bool]]:
    return [(t.kind, t.default, t.forced) for t in tracks]


def test_default_subtitle_follows_default_audio():
    tracks = _tracks("full", "forced")
    _name_tracks(tracks, audio_french=False)
    assert _defaults(tracks) == [("full", True, False), ("forced", False, True)]
    _name_tracks(tracks, audio_french=True)
    assert _defaults(tracks) == [("full", False, False), ("forced", True, True)]


def test_default_subtitle_when_a_kind_is_missing():
    only_full = _tracks("full")
    _name_tracks(only_full, audio_french=True)
    assert _defaults(only_full) == [("full", False, False)]  # French audio needs no full subtitles
    only_forced = _tracks("forced")
    _name_tracks(only_forced, audio_french=False)
    assert _defaults(only_forced) == [("forced", True, True)]


def _audio(index: int, language: str | None, default: bool) -> StreamInfo:
    return StreamInfo(index, "Audio", "aac", language, None, default, False)


def test_default_audio():
    assert default_audio([_audio(1, "jpn", False), _audio(2, "fre", True)]).language == "fre"
    assert default_audio([_audio(1, "jpn", False), _audio(2, "fre", False)]).language == "jpn"
    assert default_audio([]) is None
