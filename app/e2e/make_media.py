"""The end-to-end tests' media, synthetic: nothing copyrighted to provide.

Usage (from app/, the engine's environment has ffmpeg):
    uv run --project ../engine python e2e/make_media.py [out_dir]

Each file is a short video (720p, so the styles are scaled), an audio track
and the subtitles of MEDIA below -- what the tests expect the app to find
and write (see e2e/media.ts). The same files every time.

Rewritten only when this script changed (its hash in out_dir/stamp.txt).
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from bobinestyle.ffmpeg_backend import resolve_ffmpeg

DURATION = 30

# (language, format, title, forced) for each subtitle track; the audio's
# language decides the default subtitles (forced when it's the language's).
MEDIA = {
    # Japanese audio: the French full track becomes the default.
    "Show - E01.mkv": {
        "audio": "jpn",
        "subtitles": [("fre", "full", "French", False), ("fre", "signs", "Signs", True), ("eng", "srt", "English", False)],
    },
    # French audio: the French forced track becomes the default.
    "Show - E02.mkv": {
        "audio": "fre",
        "subtitles": [("fre", "full", "Français", False), ("fre", "signs", "Forced", True)],
    },
    # No French subtitles: nothing to do in French, English and German to restyle.
    "Show - E03.mkv": {
        "audio": "jpn",
        "subtitles": [("eng", "srt", "English", False), ("ger", "full", "Deutsch", False)],
    },
    # No subtitles at all.
    "Show - E04.mkv": {"audio": "jpn", "subtitles": []},
}

STYLES = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,40,1
Style: Italique,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,1,0,0,100,100,0,0,1,2,1,2,10,10,40,1
Style: Sign,Impact,40,&H0000FFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,8,10,10,40,1
"""


def ts(seconds: float, sep: str, digits: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    frac = f"{s % 1:.{digits}f}"[2:]
    return f"{int(h):{'02' if sep == ',' else ''}d}:{int(m):02d}:{int(s):02d}{sep}{frac}"


def write_subtitle(path: Path, kind: str) -> None:
    if kind == "srt":
        lines = [(t, t + 2, f"Line {t}") for t in range(2, DURATION - 2, 3)]
        blocks = [f"{i + 1}\n{ts(a, ',', 3)} --> {ts(b, ',', 3)}\n{text}\n" for i, (a, b, text) in enumerate(lines)]
        path.write_text("\n".join(blocks), encoding="utf-8")
        return
    if kind == "full":
        events = [(t, "Default", f"Réplique {t}") for t in range(2, DURATION - 4, 3)] + [(DURATION - 3, "Italique", "Pensée")]
    else:
        events = [(5, "Sign", "{\\pos(320,100)}PANNEAU"), (15, "Sign", "{\\pos(320,100)}AFFICHE")]
    dialogue = "\n".join(f"Dialogue: 0,{ts(a, '.', 2)},{ts(a + 2, '.', 2)},{style},,0,0,0,,{text}" for a, style, text in events)
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 640\nPlayResY: 360\n\n"
        + STYLES
        + "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + dialogue
        + "\n",
        encoding="utf-8",
    )


def make(out_dir: Path, name: str, spec: dict, tmp: Path) -> None:
    inputs = [
        *("-f", "lavfi", "-i", f"color=c=0x203048:s=1280x720:r=5:d={DURATION}"),
        *("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono"),
    ]
    maps = ["-map", "0:v", "-map", "1:a"]
    meta = ["-metadata:s:a:0", f"language={spec['audio']}", "-disposition:a:0", "default"]
    for i, (language, kind, title, forced) in enumerate(spec["subtitles"]):
        sub = tmp / f"{name}-{i}.{'srt' if kind == 'srt' else 'ass'}"
        write_subtitle(sub, kind)
        inputs += ["-i", str(sub)]
        maps += ["-map", f"{i + 2}:s"]
        meta += [f"-metadata:s:s:{i}", f"language={language}", f"-metadata:s:s:{i}", f"title={title}"]
        meta += [f"-disposition:s:{i}", "forced" if forced else "0"]
    codecs = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "40", "-pix_fmt", "yuv420p", "-c:a", "aac", "-c:s", "copy"]
    cmd = [resolve_ffmpeg(), "-v", "error", "-y", *inputs, *maps, *codecs, *meta, "-t", str(DURATION), str(out_dir / name)]
    subprocess.run(cmd, check=True)


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "media"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    stamp_file = out_dir / "stamp.txt"
    if stamp_file.exists() and stamp_file.read_text() == stamp and all((out_dir / n).exists() for n in MEDIA):
        print(f"media up to date in {out_dir}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        for name, spec in MEDIA.items():
            make(out_dir, name, spec, Path(tmp))
            print(f"made {name}")
    stamp_file.write_text(stamp)


if __name__ == "__main__":
    main()
