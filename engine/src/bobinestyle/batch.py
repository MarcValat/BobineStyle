"""Process every MKV of a folder (a season, a whole series).

Outputs mirror the source tree under one output folder (``Output`` inside
the source folder by default, as the old script did). A file whose output
already exists is skipped, so an interrupted batch can simply be run again.
One file failing never stops the others.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from bobinestyle.ffmpeg_backend import FFmpegError
from bobinestyle.fonts import system_fonts
from bobinestyle.mux import MuxError, MuxPlan, mux, plan

OUTPUT_DIR = "Output"


class Status(StrEnum):
    DONE = "done"
    PLANNED = "planned"
    EXISTS = "exists"
    NO_FRENCH = "no_french"
    ERROR = "error"


@dataclass
class FileResult:
    source: Path
    output: Path
    status: Status
    plan: MuxPlan | None = None
    error: str | None = None


def find_videos(folder: Path, recursive: bool, output_dir: Path) -> list[Path]:
    """MKV files of ``folder`` in name order, leaving out the output folder
    and unfinished ``.part.mkv`` files."""
    pattern = "**/*.mkv" if recursive else "*.mkv"
    output_dir = output_dir.resolve()
    found = []
    for path in sorted(folder.glob(pattern), key=lambda p: str(p).lower()):
        if not path.is_file() or path.name.endswith(".part.mkv"):
            continue
        if path.resolve().is_relative_to(output_dir):
            continue
        found.append(path)
    return found


def output_for(source: Path, folder: Path, output_dir: Path) -> Path:
    return output_dir / source.relative_to(folder)


def process(source: Path, output: Path, plan_only: bool = False, force: bool = False) -> FileResult:
    if output.exists() and not force:
        return FileResult(source, output, Status.EXISTS)
    try:
        p = plan(str(source))
        if not any(t.french for t in p.tracks):
            return FileResult(source, output, Status.NO_FRENCH, p)
        if plan_only:
            return FileResult(source, output, Status.PLANNED, p)
        mux(p, output)
        return FileResult(source, output, Status.DONE, p)
    except (FFmpegError, MuxError, OSError) as exc:
        return FileResult(source, output, Status.ERROR, error=str(exc).strip())


def run_batch(
    folder: Path,
    output_dir: Path | None = None,
    recursive: bool = False,
    jobs: int = 2,
    plan_only: bool = False,
    force: bool = False,
    on_result: Callable[[FileResult], None] | None = None,
) -> list[FileResult]:
    """Process every MKV of ``folder``; ``on_result`` hears about each file
    as it finishes. Results come back in file order."""
    output_dir = output_dir or folder / OUTPUT_DIR
    sources = find_videos(folder, recursive, output_dir)
    system_fonts()  # index the fonts once, before the workers need them

    def work(source: Path) -> FileResult:
        result = process(source, output_for(source, folder, output_dir), plan_only, force)
        if on_result:
            on_result(result)
        return result

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return list(pool.map(work, sources))


def summary(results: list[FileResult]) -> Iterator[tuple[Status, int]]:
    for status in Status:
        count = sum(r.status is status for r in results)
        if count:
            yield status, count
