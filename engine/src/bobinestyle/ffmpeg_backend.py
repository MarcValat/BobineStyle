from __future__ import annotations

import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from bobinestyle.cancellation import Cancelled, current_cancel_event
from bobinestyle.models import StreamInfo, SubtitleStreamInfo

# Never flash a console window per ffmpeg call once packaged without a console.
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class FFmpegError(RuntimeError):
    """Raised when the ffmpeg binary is missing or a media operation fails."""


@lru_cache(maxsize=1)
def resolve_ffmpeg() -> str:
    """Locate an ffmpeg executable: prefer one on PATH, else the bundled one."""
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - defensive
        raise FFmpegError("ffmpeg not found: neither on PATH nor through the imageio-ffmpeg package.") from exc


# How often a running ffmpeg checks for a cancellation.
_CANCEL_POLL_S = 0.2
_TOTAL_SIZE_RE = re.compile(rb"^total_size=(\d+)")


def _run(cmd: list[str], cwd: Path | None = None, on_size: Callable[[int], None] | None = None) -> subprocess.CompletedProcess[bytes]:
    """Run ffmpeg, killing it (raising ``Cancelled``) as soon as the job
    running it is cancelled. With ``on_size``, ffmpeg reports how far it
    got (bytes written) as it goes: its output time is often unknown
    ("N/A") when copying with -copyts and attachments."""
    event = current_cancel_event()
    if event is None and on_size is None:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, creationflags=_SUBPROCESS_FLAGS)
    if event is not None and event.is_set():
        raise Cancelled()
    if on_size is not None:
        cmd = [cmd[0], "-progress", "pipe:1", "-nostats", *cmd[1:]]
    with subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=_SUBPROCESS_FLAGS
    ) as proc:
        out: list[bytes] = []
        err: list[bytes] = []

        def read_out() -> None:
            for line in proc.stdout:
                out.append(line)
                if on_size and (match := _TOTAL_SIZE_RE.match(line)):
                    on_size(int(match.group(1)))

        readers = [
            threading.Thread(target=read_out, daemon=True),
            threading.Thread(target=lambda: err.append(proc.stderr.read()), daemon=True),
        ]
        for reader in readers:
            reader.start()
        while True:
            try:
                proc.wait(timeout=_CANCEL_POLL_S)
                break
            except subprocess.TimeoutExpired:
                if event is not None and event.is_set():
                    proc.kill()
                    proc.wait()
                    raise Cancelled() from None
        for reader in readers:
            reader.join()
    return subprocess.CompletedProcess(cmd, proc.returncode, b"".join(out), b"".join(err))


def run_checked(cmd: list[str], on_size: Callable[[int], None] | None = None) -> bytes:
    proc = _run(cmd, on_size=on_size)
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg failed:\n{' '.join(cmd)}\n{proc.stderr.decode(errors='replace')}")
    return proc.stdout


def ffmpeg_info(path: str) -> str:
    """``ffmpeg -i path``'s report."""
    if not Path(path).is_file():
        raise FFmpegError(f"File not found: {path}")
    proc = _run([resolve_ffmpeg(), "-hide_banner", "-i", path])
    # UTF-8 explicitly: ffmpeg writes tags that way, cp1252 would mangle titles.
    info = proc.stderr.decode("utf-8", errors="replace")
    if "Invalid data found" in info:
        raise FFmpegError(f"Cannot read {path!r}:\n{info}")
    return info


_STREAM_RE = re.compile(
    r"^\s*Stream #\d+:(?P<index>\d+)(?:\[[^\]]*\])?(?:\((?P<lang>[^)]+)\))?:\s*(?P<kind>\w+):\s*(?P<codec>[^,\s]+)?"
)
# ", 1920x1080 [SAR 1:1 DAR 16:9]" (the codec tag "0x31637661" has no comma before it).
_SIZE_RE = re.compile(r",\s(?P<w>\d+)x(?P<h>\d+)(?:\s\[SAR (?P<sn>\d+):(?P<sd>\d+) DAR \d+:\d+\])?")
_TAG_RE = re.compile(r"^\s+(?P<key>title|filename)\s*: (?P<value>.*)$")
_FORCED_TITLE_RE = re.compile(r"forc", re.IGNORECASE)


def parse_streams(info: str) -> list[StreamInfo]:
    """Every stream of an ``ffmpeg -i`` report, in container order."""
    streams: list[dict] = []
    current: dict | None = None
    for line in info.splitlines():
        if match := _STREAM_RE.match(line):
            current = {
                "index": int(match["index"]),
                "kind": match["kind"],
                "codec": match["codec"],
                "language": match["lang"] if match["lang"] not in (None, "und") else None,
                "title": None,
                "filename": None,
                "default": "(default)" in line,
                "forced": "(forced)" in line,
                "attached_pic": "(attached pic)" in line,
            }
            if current["kind"] == "Video" and (size := _SIZE_RE.search(line)):
                current["width"], current["height"] = int(size["w"]), int(size["h"])
                if size["sn"]:
                    current["sar"] = (int(size["sn"]), int(size["sd"]))
            streams.append(current)
        elif current is not None and (tag := _TAG_RE.match(line)):
            if current[tag["key"]] is None:
                current[tag["key"]] = tag["value"].strip()
        elif not line.startswith(" "):
            current = None
    return [StreamInfo(**s) for s in streams]


def probe_streams(path: str) -> list[StreamInfo]:
    return parse_streams(ffmpeg_info(path))


_DURATION_RE = re.compile(r"Duration:\s*(?P<h>\d+):(?P<m>\d+):(?P<s>\d+(?:\.\d+)?)")


def container_duration(info: str) -> float | None:
    match = _DURATION_RE.search(info)
    return int(match["h"]) * 3600 + int(match["m"]) * 60 + float(match["s"]) if match else None


def dump_attachments(path: str, folder: Path) -> list[Path]:
    """Write ``path``'s attachments (fonts) into ``folder``."""
    before = set(folder.iterdir())
    # ffmpeg dumps before complaining that there is no output: ignore that.
    _run(
        [resolve_ffmpeg(), "-hide_banner", "-loglevel", "quiet", "-y", "-dump_attachment:t", "", "-i", str(Path(path).resolve())],
        cwd=folder,
    )
    return sorted(set(folder.iterdir()) - before)


TEXT_FORMATS = {"ass": "ass", "ssa": "ass", "subrip": "srt", "srt": "srt"}


def extract_subtitle_text(path: str, track: int, codec: str) -> str:
    """Subtitle stream ``0:s:track`` as text, unconverted: ASS keeps its
    header and styles, SRT stays SRT. ``-copyts`` keeps the container's
    timestamps (ffmpeg otherwise shifts them by the file's start time)."""
    fmt = TEXT_FORMATS.get(codec)
    if fmt is None:
        raise FFmpegError(f"Unsupported subtitle format: {codec}")
    proc = _run(
        [
            resolve_ffmpeg(), "-hide_banner", "-loglevel", "error", "-copyts", "-i", path,
            "-map", f"0:s:{track}", "-c:s", "copy", "-f", fmt, "-",
        ]
    )
    if proc.returncode != 0:
        raise FFmpegError(f"Cannot extract subtitle track {track}:\n{proc.stderr.decode(errors='replace')}")
    return proc.stdout.decode("utf-8-sig", errors="replace").replace("\r\n", "\n")


def main_video(streams: list[StreamInfo]) -> StreamInfo | None:
    """The first real video stream (cover art is skipped)."""
    return next((s for s in streams if s.kind == "Video" and not s.attached_pic and s.width), None)


def subtitle_streams(streams: list[StreamInfo]) -> list[SubtitleStreamInfo]:
    """The subtitle streams, indexed like ffmpeg's ``0:s:N``."""
    subs = [s for s in streams if s.kind == "Subtitle"]
    return [
        SubtitleStreamInfo(
            index=n,
            global_index=s.index,
            codec=s.codec or "?",
            language=s.language,
            title=s.title,
            default=s.default,
            forced=s.forced or bool(s.title and _FORCED_TITLE_RE.search(s.title)),
        )
        for n, s in enumerate(subs)
    ]
