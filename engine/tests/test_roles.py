from __future__ import annotations

import subprocess
from pathlib import Path

from bobinestyle.ass import parse_ass, parse_color, parse_time
from bobinestyle.ffmpeg_backend import extract_subtitle_text, resolve_ffmpeg
from bobinestyle.roles import Role, analyze

STYLE_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
    "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding"
)


def _style(name: str, italic: int = 0, align: int = 2, color: str = "&H00FFFFFF", margin: int = 10) -> str:
    return (
        f"Style: {name},Arial,48,{color},&H000000FF,&H00000000,&H00000000,0,{italic},0,0,100,100,0,0,1,2,1,"
        f"{align},{margin},{margin},40,1"
    )


def _line(start: int, style: str, text: str, actor: str = "") -> str:
    return f"Dialogue: 0,0:00:{start:02d}.00,0:00:{start + 2:02d}.00,{style},{actor},0,0,0,,{text}"


def _script(styles: list[str], events: list[str], info: str = "PlayResX: 1920\nPlayResY: 1080\n") -> str:
    return (
        f"[Script Info]\nScriptType: v4.00+\n{info}\n[V4+ Styles]\n{STYLE_FORMAT}\n"
        + "\n".join(styles)
        + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(events)
        + "\n"
    )


FANSUB = _script(
    [
        _style("Dialogues"),
        _style("Pensées", italic=1),
        _style("Haut", align=8),
        _style("Deux personnes", align=1),
        _style("Simultané", color="&H0000FFFF"),
        _style("Large", margin=200),
        _style("Panneau"),
        _style("Jamais utilisé"),
    ],
    [_line(t, "Dialogues", f"Réplique {t}") for t in range(0, 40, 3)]
    + [_line(1, "Pensées", "Je dois y aller."), _line(50, "Pensées", "Vite.")]
    + [_line(52, "Haut", "En haut")]
    + [_line(54, "Deux personnes", "- Oui ?\\N- Non.")]
    + [_line(t + 1, "Simultané", "En même temps") for t in (3, 9, 15)]
    + [_line(56, "Large", "Avec marges")]
    + [_line(58, "Panneau", "{\\pos(100,200)\\fs30}PHARMACIE", "Sign")]
    + [_line(30, "Dialogues", "{\\an7\\pos(10,10)}Titre")],
)


def _roles(text: str) -> dict[str, Role]:
    return {r.style.name: r.role for r in analyze(parse_ass(text)).styles}


def test_roles_from_usage_not_names():
    assert _roles(FANSUB) == {
        "Dialogues": Role.DIALOGUE,
        "Pensées": Role.ITALIC,
        "Haut": Role.TOP,
        "Deux personnes": Role.DASHES,
        "Simultané": Role.OVERLAP,
        "Large": Role.MARGINS,
        "Panneau": Role.TYPESETTING,
        "Jamais utilisé": Role.UNUSED,
    }


def test_positioned_lines_keep_play_res():
    report = analyze(parse_ass(FANSUB))
    assert report.positioned_lines == 2
    assert report.keep_play_res
    assert report.play_res == (1920, 1080)


def test_inline_tags_give_the_role():
    """A style used with \\an8 or \\i1 on most of its lines is a top or
    italic style, whatever its own definition."""
    text = _script(
        [_style("Default"), _style("Alt")],
        [_line(t, "Default", "Texte") for t in range(0, 30, 3)]
        + [_line(31, "Alt", "{\\an8\\i1}Haut"), _line(34, "Alt", "{\\i1\\an8}Haut aussi")],
    )
    assert _roles(text)["Alt"] is Role.TOP_ITALIC


def test_signs_only_track_is_left_alone():
    text = _script(
        [_style("Default")],
        [_line(1, "Default", "{\\pos(10,10)}PANNEAU"), _line(5, "Default", "{\\fs18\\an1}Générique")],
        info="",
    )
    report = analyze(parse_ass(text))
    assert [r.role for r in report.styles] == [Role.TYPESETTING]
    assert report.play_res is None
    assert report.dialogue_lines == 0


def test_play_res_fallbacks_and_header_values():
    doc = parse_ass(_script([], [], info="PlayResY: 720\nScaledBorderAndShadow: Yes\n"))
    assert doc.play_res == (960, 720)
    assert doc.scaled_border_and_shadow


def test_ssa_alignment_and_duplicate_styles():
    text = (
        "[Script Info]\nScriptType: v4.00\n\n[V4 Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,TertiaryColour,BackColour,Bold,Italic,"
        "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,AlphaLevel,Encoding\n"
        "Style: Top,Arial,20,16777215,255,0,0,0,0,1,2,0,6,10,10,10,0,1\n"
        "Style: Top,Arial,20,16777215,255,0,0,0,-1,1,2,0,2,10,10,10,0,1\n"
    )
    doc = parse_ass(text)
    assert doc.styles[0].alignment == 8
    assert doc.style("Top").italic and doc.style("Top").alignment == 2


def test_parsers():
    assert parse_time("1:02:03.45") == 3723.45
    assert parse_color("&H0000FFFF") == (255, 255, 0, 0)
    assert parse_color("16777215") == (255, 255, 255, 0)


def test_extract_ass_from_mkv(tmp_path: Path):
    src = tmp_path / "in.ass"
    src.write_text(FANSUB, encoding="utf-8")
    mkv = tmp_path / "in.mkv"
    subprocess.run(
        [
            resolve_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=64x36:r=5:d=60", "-i", str(src),
            "-map", "0", "-map", "1", "-c:v", "mpeg4", "-c:s", "copy", str(mkv),
        ],
        check=True,
    )
    doc = parse_ass(extract_subtitle_text(str(mkv), 0, "ass"))
    assert [s.name for s in doc.styles] == [s.name for s in parse_ass(FANSUB).styles]
    assert len(doc.events) == len(parse_ass(FANSUB).events)
    assert _roles(extract_subtitle_text(str(mkv), 0, "ass")) == _roles(FANSUB)


def test_default_full_of_signs_still_carries_the_dialogue():
    """An opening full of signs typeset with Default (Crunchyroll) must not
    make Italique the main style and cost it its italic."""
    text = _script(
        [_style("Default"), _style("Italique", italic=1), _style("Signs")],
        [_line(t, "Default", "{\pos(10,10)\fs20}PANNEAU", "Sign") for t in range(0, 40)]
        + [_line(t, "Default", "Réplique") for t in range(41, 45)]
        + [_line(t, "Italique", "Pensée") for t in range(46, 56)]
        + [_line(t, "Signs", "Texte sans balise") for t in range(0, 6)],
    )
    roles = _roles(text)
    assert roles == {"Default": Role.DIALOGUE, "Italique": Role.ITALIC, "Signs": Role.TYPESETTING}


def test_italic_only_dialogue_stays_italic():
    text = _script([_style("Pensées", italic=1)], [_line(t, "Pensées", "Hmm") for t in range(0, 20, 2)])
    assert _roles(text) == {"Pensées": Role.ITALIC}
