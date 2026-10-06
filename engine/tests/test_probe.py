from __future__ import annotations

import subprocess
from pathlib import Path

from bobinestyle.ffmpeg_backend import main_video, parse_streams, probe_streams, resolve_ffmpeg, subtitle_streams

ANIME = """\
Input #0, matroska,webm, from 'episode.mkv':
  Duration: 00:24:49.10, start: 0.000000, bitrate: 8247 kb/s
  Stream #0:0(jpn): Video: h264 (High), yuv420p(progressive), 1920x1080 [SAR 1:1 DAR 16:9], 23.98 fps, 23.98 tbr, 1k tbn (default)
  Stream #0:1(jpn): Audio: aac (LC), 44100 Hz, stereo, fltp (default)
  Stream #0:3(fre): Subtitle: ass (ssa) (default)
    Metadata:
      title           : French
  Stream #0:4(fre): Subtitle: ass (ssa)
    Metadata:
      title           : French Signs
  Stream #0:5: Attachment: none
    Metadata:
      filename        : trebucbd_0.ttf
      mimetype        : font/ttf
"""

DVD = """\
Input #0, matroska,webm, from 'dvd.mkv':
  Stream #0:0: Video: mjpeg (Baseline), yuvj420p(pc), 600x600 [SAR 1:1 DAR 1:1], 90k tbr, 90k tbn (attached pic)
  Stream #0:1(fre): Video: mpeg2video (Main) (mp2v / 0x7632706D), yuv420p(tv, top first), 720x576 [SAR 64:45 DAR 16:9], 25 fps
  Stream #0:2(und): Subtitle: subrip (srt) (forced)
"""


def test_parse_anime_report():
    streams = parse_streams(ANIME)
    video = main_video(streams)
    assert (video.width, video.height, video.sar, video.display_size) == (1920, 1080, (1, 1), (1920, 1080))
    subs = subtitle_streams(streams)
    assert [(s.index, s.global_index, s.codec, s.language, s.title) for s in subs] == [
        (0, 3, "ass", "fre", "French"),
        (1, 4, "ass", "fre", "French Signs"),
    ]
    assert [(s.default, s.forced) for s in subs] == [(True, False), (False, False)]
    assert [s.filename for s in streams if s.kind == "Attachment"] == ["trebucbd_0.ttf"]


def test_anamorphic_video_and_cover_art():
    streams = parse_streams(DVD)
    video = main_video(streams)
    assert video.index == 1  # the cover is skipped
    assert (video.width, video.height) == (720, 576)
    assert video.display_size == (1024, 576)
    [sub] = subtitle_streams(streams)
    assert (sub.language, sub.forced) == (None, True)


def test_forced_from_title():
    report = "  Stream #0:0(fre): Subtitle: ass (ssa)\n    Metadata:\n      title           : Français (forcés)\n"
    assert subtitle_streams(parse_streams(report))[0].forced


def test_probe_real_mkv(tmp_path: Path):
    """An anamorphic video plus a titled French SRT, through ffmpeg."""
    srt = tmp_path / "fr.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nBonjour\n", encoding="utf-8")
    out = tmp_path / "in.mkv"
    subprocess.run(
        [
            resolve_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=72x58:r=5:d=3", "-i", str(srt),
            "-map", "0", "-map", "1", "-vf", "setsar=64/45", "-c:v", "mpeg4", "-c:s", "copy",
            "-metadata:s:s:0", "language=fre", "-metadata:s:s:0", "title=Français", str(out),
        ],
        check=True,
    )
    streams = probe_streams(str(out))
    assert main_video(streams).display_size == (102, 58)
    [sub] = subtitle_streams(streams)
    assert (sub.codec, sub.language, sub.title) == ("subrip", "fre", "Français")
