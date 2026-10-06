from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bobinestyle.ass import parse_ass
from bobinestyle.ffmpeg_backend import extract_subtitle_text, probe_streams, resolve_ffmpeg, subtitle_streams
from bobinestyle.fonts import faces_for, system_fonts
from bobinestyle.mux import FULL_TITLE, mux, plan
from bobinestyle.srt import Cue, html_to_ass, parse_srt, srt_to_ass

DEMO = """﻿1
00:00:27,920 --> 00:00:29,840
Si on gagne, on jouera la Coupe !

2
00:00:30.000 --> 00:00:31.500
<i>Je dois absolument marquer.</i>

3
00:00:38,930 --> 00:00:41,270
{\\an8}Marque !
C'est la dernière occasion !

4
00:01:18,550 --> 00:01:20,510
– On contre-attaque !
– Montez !

5
00:01:21,000 --> 00:01:23,000
Un <i>mot</i> en italique
et <font color="#ff8000">de l'orange</font>.

6
00:01:22,000 --> 00:01:24,000
Je parle en même temps !

7
00:01:30,000 --> 00:01:32,000
<i>- Toi ?</i>
<i>- Moi.</i>
"""

HAS_TREBUCHET = bool(faces_for("trebuchet ms", system_fonts()))


def _events(text: str) -> list[tuple[str, str, str]]:
    doc = parse_ass(text)
    return [(e.style, e.fields["marginl"], e.text) for e in doc.events]


def test_parse_srt_tolerates_quirks():
    cues = parse_srt("1\r\n00:00:01,000 --> 00:00:02,500\r\nUn\r\n\r\nsuite\r\n\r\n2\r\n00:00:03.25 --> 00:00:04,000\r\nDeux\r\n")
    assert cues == [Cue(1.0, 2.5, "Un\nsuite"), Cue(3.25, 4.0, "Deux")]


def test_html_to_ass():
    assert html_to_ass('<i>a</i>\n<b>b</b> <font color="#FF8000">c</font> <font face="Arial">d</font>') == (
        "{\\i1}a{\\i0}\\N{\\b1}b{\\b0} {\\c&H0080FF&}c{\\c} d{\\c}"
    )


def test_each_cue_gets_its_house_style():
    events = _events(srt_to_ass(parse_srt(DEMO), (1920, 1080)))
    assert [(style, text) for style, _, text in events] == [
        ("Default", "Si on gagne, on jouera la Coupe !"),
        ("Italique", "Je dois absolument marquer."),
        ("DefaultTop", "Marque !\\NC'est la dernière occasion !"),
        ("TiretsDefault", "– On contre-attaque !\\N– Montez !"),
        ("Default", "Un {\\i1}mot{\\i0} en italique\\Net {\\c&H0080FF&}de l'orange{\\c}."),
        ("Overlap", "Je parle en même temps !"),
        ("TiretsItalique", "- Toi ?\\N- Moi."),
    ]
    doc = parse_ass(srt_to_ass(parse_srt(DEMO), (1920, 1080)))
    assert doc.play_res == (1920, 1080) and doc.scaled_border_and_shadow
    assert [e.fields["start"] for e in doc.events[:2]] == ["0:00:27.92", "0:00:30.00"]
    assert {s.name for s in doc.styles} == {
        "Default", "Italique", "DefaultTop", "TiretsDefault", "TiretsItalique", "Overlap",
    }
    assert doc.style("Default").fields["fontsize"] == "66"


@pytest.mark.skipif(not HAS_TREBUCHET, reason="Trebuchet MS not installed")
def test_dash_block_is_centred_like_crunchyroll():
    """Crunchyroll centres this exact line with MarginL 226 in a 640x360 grid."""
    events = _events(srt_to_ass(parse_srt(DEMO), (640, 360)))
    assert events[3][1] == "0226"


def test_small_overlaps_are_timing_slop():
    cues = [Cue(1.0, 3.0, "A"), Cue(2.9, 5.0, "B")]
    assert [style for style, _, _ in _events(srt_to_ass(cues, None))] == ["Default", "Default"]


def test_mux_converts_french_srt(tmp_path: Path):
    srt = tmp_path / "fr.srt"
    srt.write_text(DEMO, encoding="utf-8")
    mkv = tmp_path / "in.mkv"
    subprocess.run(
        [
            resolve_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=192x108:r=5:d=95", "-i", str(srt),
            "-map", "0", "-map", "1", "-c:v", "mpeg4", "-c:s", "copy",
            "-metadata:s:s:0", "language=fre", str(mkv),
        ],
        check=True,
    )
    out = mux(plan(str(mkv)), tmp_path / "out.mkv")
    [sub] = subtitle_streams(probe_streams(str(out)))
    assert (sub.codec, sub.title, sub.default) == ("ass", FULL_TITLE, True)
    doc = parse_ass(extract_subtitle_text(str(out), 0, "ass"))
    assert doc.play_res == (192, 108)
    assert [e.style for e in doc.events][:4] == ["Default", "Italique", "DefaultTop", "TiretsDefault"]
