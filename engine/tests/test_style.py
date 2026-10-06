from __future__ import annotations

from bobinestyle.ass import parse_ass
from bobinestyle.style import apply_house_style
from test_roles import FANSUB, _line, _script, _style


def _styles(text: str) -> dict[str, dict[str, str]]:
    return {s.name: s.fields for s in parse_ass(text).styles}


def _events(text: str) -> list[str]:
    doc = parse_ass(text)
    return [doc.lines[e.line_index] for e in doc.events]


CRUNCHYROLL = _script(
    [_style("Default"), _style("Italique", italic=1), _style("TiretsDefault", align=1)],
    [_line(t, "Default", "Réplique") for t in range(0, 30, 3)]
    + [_line(31, "Italique", "Pensée"), _line(40, "TiretsDefault", "- Oui !\\N- Non !")]
    + [_line(45, "Default", "{\\fs16\\pos(320,100)}PANNEAU", "Sign")],
    info="PlayResX: 640\nPlayResY: 360\nScaledBorderAndShadow: yes\n",
)


def test_positioned_script_keeps_its_grid():
    result = apply_house_style(CRUNCHYROLL, (1920, 1080))
    assert (result.play_res, result.play_res_changed) == ((640, 360), False)
    styles = _styles(result.text)
    default = styles["Default"]
    assert (default["fontname"], default["fontsize"], default["outline"], default["shadow"]) == (
        "Trebuchet MS", "22", "0.83", "0.83",
    )
    assert (default["marginl"], default["marginr"], default["marginv"], default["bold"]) == ("2", "2", "25", "-1")
    assert styles["Italique"]["italic"] == "-1"
    assert (styles["TiretsDefault"]["alignment"], styles["TiretsDefault"]["marginl"]) == ("1", "22")
    # Events are untouched, byte for byte.
    assert _events(result.text) == _events(CRUNCHYROLL)


def test_unpinned_script_takes_the_video_grid():
    text = _script(
        [_style("Default")],
        [_line(t, "Default", "{\\i1}Réplique") for t in range(0, 30, 3)]
        + ["Dialogue: 0,0:00:40.00,0:00:42.00,Default,,0300,0000,0000,,Décalé"],
    )
    result = apply_house_style(text, (1280, 720))
    assert (result.play_res, result.play_res_changed) == ((1280, 720), True)
    info = parse_ass(result.text)
    assert info.play_res == (1280, 720)
    assert info.scaled_border_and_shadow
    default = _styles(result.text)["Default"]
    assert (default["fontsize"], default["outline"], default["marginv"], default["marginl"]) == ("44", "1.67", "50", "4")
    # Per-line margins follow the new grid, zero-padded as before.
    assert _events(result.text)[-1] == "Dialogue: 0,0:00:40.00,0:00:42.00,Default,,0200,0000,0000,,Décalé"


def test_scope_and_four_thirds_keep_the_on_screen_size():
    text = _script([_style("Default")], [_line(t, "Default", "Texte") for t in range(0, 30, 3)])
    for size in ((1920, 800), (1440, 1080)):
        result = apply_house_style(text, size)
        assert result.play_res == size
        assert _styles(result.text)["Default"]["fontsize"] == "66"


def test_missing_play_res_with_signs_is_made_explicit():
    text = _script(
        [_style("Default")],
        [_line(t, "Default", "Texte") for t in range(0, 30, 3)] + [_line(40, "Default", "{\\pos(10,10)}X")],
        info="",
    )
    result = apply_house_style(text, (1920, 1080))
    assert parse_ass(result.text).play_res == (384, 288)
    assert _styles(result.text)["Default"]["fontsize"] == "17.6"


def test_roles_get_their_variant_and_typesetting_is_kept():
    result = apply_house_style(FANSUB, (1920, 1080))
    styles = _styles(result.text)
    assert styles["Haut"]["alignment"] == "8"
    assert styles["Simultané"]["primarycolour"] == "&H008CEEFA"
    assert (styles["Large"]["marginl"], styles["Large"]["marginr"]) == ("51", "51")
    assert styles["Panneau"] == _styles(FANSUB)["Panneau"]
    assert styles["Jamais utilisé"] == _styles(FANSUB)["Jamais utilisé"]


def test_warnings():
    mismatch = apply_house_style(CRUNCHYROLL.replace("PlayResY: 360", "PlayResY: 480"), (1920, 1080))
    assert any("proportions" in w for w in mismatch.warnings)
    borders = CRUNCHYROLL.replace("ScaledBorderAndShadow: yes", "ScaledBorderAndShadow: no").replace(
        "\\fs16", "\\fs16\\bord2"
    )
    result = apply_house_style(borders, (1920, 1080))
    assert any("ScaledBorderAndShadow" in w for w in result.warnings)
    assert parse_ass(result.text).scaled_border_and_shadow


def test_ssa_alignment_written_back():
    text = (
        "[Script Info]\nScriptType: v4.00\nPlayResX: 640\nPlayResY: 480\n\n[V4 Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,TertiaryColour,BackColour,Bold,Italic,"
        "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,AlphaLevel,Encoding\n"
        "Style: Default,Arial,20,16777215,255,0,0,0,0,1,2,0,2,10,10,10,0,1\n"
        "Style: Up,Arial,20,16777215,255,0,0,0,0,1,2,0,6,10,10,10,0,1\n\n"
        "[Events]\nFormat: Marked,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        + "\n".join(f"Dialogue: Marked=0,0:00:{t:02d}.00,0:00:{t + 1:02d}.00,Default,,0,0,0,,A" for t in range(0, 20, 2))
        + "\nDialogue: Marked=0,0:00:30.00,0:00:31.00,Up,,0,0,0,,B\n"
    )
    result = apply_house_style(text, (640, 480))
    up = parse_ass(result.text).style("Up")
    assert up.fields["alignment"] == "6" and up.alignment == 8
