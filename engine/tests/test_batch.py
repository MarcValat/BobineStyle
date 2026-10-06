from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from bobinestyle.batch import Status, find_videos, run_batch
from bobinestyle.cli import main
from bobinestyle.ffmpeg_backend import resolve_ffmpeg
from test_mux import FULL

ENGLISH = "1\n00:00:01,000 --> 00:00:02,000\nHello\n"


def _mkv(path: Path, subtitle: Path, language: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            resolve_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=64x36:r=5:d=45", "-i", str(subtitle),
            "-map", "0", "-map", "1", "-c:v", "mpeg4", "-c:s", "copy",
            "-metadata:s:s:0", f"language={language}", str(path),
        ],
        check=True,
    )


@pytest.fixture
def series(tmp_path: Path) -> Path:
    """S01 with two French episodes, S02 with an English-only one and a
    broken file."""
    (tmp_path / "fr.ass").write_text(FULL, encoding="utf-8")
    (tmp_path / "en.srt").write_text(ENGLISH, encoding="utf-8")
    root = tmp_path / "Série"
    _mkv(root / "S01" / "E01.mkv", tmp_path / "fr.ass", "fre")
    _mkv(root / "S01" / "E02.mkv", tmp_path / "fr.ass", "fre")
    _mkv(root / "S02" / "E01.mkv", tmp_path / "en.srt", "eng")
    (root / "S02" / "E02.mkv").write_bytes(b"not a video")
    (root / "S02" / "E03.part.mkv").write_bytes(b"unfinished")
    return root


def _statuses(results) -> dict[str, Status]:
    return {r.source.relative_to(r.source.parents[1]).as_posix(): r.status for r in results}


def test_batch_mirrors_the_tree_and_keeps_going(series: Path):
    results = run_batch(series, recursive=True)
    assert _statuses(results) == {
        "S01/E01.mkv": Status.DONE,
        "S01/E02.mkv": Status.DONE,
        "S02/E01.mkv": Status.NO_FRENCH,
        "S02/E02.mkv": Status.ERROR,
    }
    assert (series / "Output" / "S01" / "E01.mkv").is_file()
    assert (series / "Output" / "S01" / "E02.mkv").is_file()
    assert not (series / "Output" / "S02").exists()


def test_rerun_skips_done_files_and_ignores_the_output(series: Path):
    run_batch(series, recursive=True)
    assert [p.relative_to(series).as_posix() for p in find_videos(series, True, series / "Output")] == [
        "S01/E01.mkv", "S01/E02.mkv", "S02/E01.mkv", "S02/E02.mkv",
    ]
    again = _statuses(run_batch(series, recursive=True))
    assert again["S01/E01.mkv"] is Status.EXISTS
    forced = _statuses(run_batch(series, recursive=True, force=True))
    assert forced["S01/E01.mkv"] is Status.DONE


def test_output_folders_of_seasons_are_skipped(series: Path, tmp_path: Path):
    """The app writes next to each file (S01/Output): scanning the series
    again must not pick those up."""
    (series / "S01" / "Output").mkdir()
    (series / "S01" / "Output" / "E01.mkv").write_bytes(b"")
    found = find_videos(series, True, tmp_path / "elsewhere")
    assert "S01/Output/E01.mkv" not in [p.relative_to(series).as_posix() for p in found]


def test_plan_only_writes_nothing(series: Path, tmp_path: Path):
    out = tmp_path / "ailleurs"
    results = run_batch(series / "S01", output_dir=out, plan_only=True)
    assert {r.status for r in results} == {Status.PLANNED}
    assert not out.exists()


def test_not_recursive_by_default(series: Path):
    assert run_batch(series) == []


def test_cli_batch(series: Path):
    result = CliRunner().invoke(main, ["batch", str(series), "-r", "-j", "1"])
    assert result.exit_code == 1  # the broken file
    assert "✓ S01" in result.output and "✗ S02" in result.output
    assert "Bilan : 2 traité(s), 1 sans sous-titres français, 1 en erreur" in result.output
