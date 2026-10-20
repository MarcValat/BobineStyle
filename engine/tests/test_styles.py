"""Styles of the user's own: their look, their variants, where they're kept."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_mux import mkv  # noqa: F401 - fixture

from bobinestyle.ass import parse_ass
from bobinestyle.mux import plan
from bobinestyle.roles import Role
from bobinestyle.server import app
from bobinestyle.style import house_fields
from bobinestyle.styles import HOUSE, SubtitleStyle, ass_color, read_styles, write_styles

YELLOW = replace(HOUSE, name="Jaune", font="Arial", size=80, bold=False, color="#FFE066", outline=3)


def test_house_style_is_the_old_fixed_one():
    fields = house_fields(Role.DIALOGUE, 1, 1)
    assert (fields["fontname"], fields["fontsize"], fields["bold"]) == ("Trebuchet MS", "66", "-1")
    assert (fields["primarycolour"], fields["outline"], fields["marginv"]) == ("&H00FFFFFF", "2.5", "75")
    assert house_fields(Role.OVERLAP, 1, 1)["primarycolour"] == "&H008CEEFA"


def test_colors_in_ass_order():
    assert ass_color("#FFE066") == "&H0066E0FF"
    assert ass_color("#faee8c") == "&H008CEEFA"


def test_a_style_of_ones_own():
    fields = house_fields(Role.DIALOGUE, 1, 1, YELLOW)
    assert (fields["fontname"], fields["fontsize"], fields["bold"], fields["outline"]) == ("Arial", "80", "0", "3")
    assert fields["primarycolour"] == "&H0066E0FF"
    # Sizes scale with the video, as the house style's.
    assert house_fields(Role.DIALOGUE, 2, 2, YELLOW)["fontsize"] == "160"


def test_variants_turned_off_take_the_dialogue_look():
    off = replace(
        HOUSE,
        italic_variant=False,
        top_variant=False,
        dashes_variant=False,
        overlap_variant=False,
        margins_variant=False,
    )
    dialogue = house_fields(Role.DIALOGUE, 1, 1, off)
    for role in (Role.ITALIC, Role.TOP, Role.DASHES, Role.OVERLAP, Role.MARGINS):
        assert house_fields(role, 1, 1, off) == dialogue, role


def test_variants_change_what_they_say():
    top = replace(HOUSE, top_margin=40)
    assert (house_fields(Role.TOP, 1, 1, top)["alignment"], house_fields(Role.TOP, 1, 1, top)["marginv"]) == ("8", "40")
    wide = replace(HOUSE, margins_extra=100)
    assert house_fields(Role.MARGINS, 1, 1, wide)["marginl"] == "106"
    # An italic main style: its italic variant stands out upright.
    slanted = replace(HOUSE, italic=True)
    assert house_fields(Role.DIALOGUE, 1, 1, slanted)["italic"] == "-1"
    assert house_fields(Role.ITALIC, 1, 1, slanted)["italic"] == "0"


def test_a_style_is_checked():
    with pytest.raises(ValueError):
        replace(HOUSE, color="yellow")
    with pytest.raises(ValueError):
        replace(HOUSE, size=0)
    with pytest.raises(ValueError):
        replace(HOUSE, name=" ")
    # Fields it doesn't know are left out, missing ones are the house style's.
    assert SubtitleStyle.of({"name": "A", "unknown": 1}) == replace(HOUSE, name="A")


def test_styles_kept_in_the_data_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BOBINESTYLE_DATA", str(tmp_path))
    assert read_styles() == []
    write_styles([YELLOW])
    assert read_styles() == [YELLOW]
    assert (tmp_path / "styles.json").is_file()
    (tmp_path / "styles.json").write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        read_styles()


def test_plan_in_a_style(mkv: Path):  # noqa: F811
    p = plan(str(mkv), style=YELLOW)
    full = p.tracks[1]
    assert parse_ass(full.text).style("Default").fontname == "Arial"
    assert "arial" in {n for f in p.fonts for n in f.families} or "arial" in p.fonts_missing


client = TestClient(app)


def test_styles_through_the_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BOBINESTYLE_DATA", str(tmp_path))
    assert client.get("/styles").json() == {"styles": []}
    assert client.put("/styles", json={"styles": [YELLOW.to_json()]}).status_code == 204
    assert client.get("/styles").json()["styles"][0]["name"] == "Jaune"
    assert client.put("/styles", json={"styles": [{"color": "nope"}]}).status_code == 400

    exported = tmp_path / "shared" / "mes styles.json"
    assert client.post("/styles/export", json={"path": str(exported), "styles": [YELLOW.to_json()]}).status_code == 204
    assert client.post("/styles/import", json={"path": str(exported)}).json()["styles"][0]["font"] == "Arial"
    (tmp_path / "bad.json").write_text("{}", encoding="utf-8")
    assert client.post("/styles/import", json={"path": str(tmp_path / "bad.json")}).status_code == 400

    assert "fonts" in client.get("/fonts").json()


def test_plan_takes_a_style(mkv: Path):  # noqa: F811
    assert client.post("/plan", json={"path": str(mkv), "style": YELLOW.to_json()}).status_code == 200
    assert client.post("/plan", json={"path": str(mkv), "style": {"size": -1}}).status_code == 400
