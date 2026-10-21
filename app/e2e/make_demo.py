"""The docs' demo series, synthetic as the tests' media (make_media.py):
"Les Phares du Nord", episodes as long as a real one, with lines of
dialogue written here and the styles a release would have (thin Arial,
italics, dash lines, signs). Nothing copyrighted: no text or timing taken
from a real release.

Usage (from app/; e2e/docs.spec.ts runs it):
    uv run --project ../engine python e2e/make_demo.py [out_dir]

In out_dir/Les Phares du Nord/Saison 1: S01E01 (English audio; French full
and forced ASS, English SRT), S01E02 (English audio; French full SRT,
English SRT), S01E03 (French audio; French full and forced ASS, English
SRT) and a bonus without subtitles. Rewritten only when this script or
make_media.py changed.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from bobinestyle.ffmpeg_backend import resolve_ffmpeg
from make_media import ts

SERIES = "Les Phares du Nord"
DURATION = 1320
STEP = 4

LINES = [
    (
        "Le phare n'a pas fonctionné cette nuit.",
        "The lighthouse didn't work last night.",
    ),
    ("Qui était de garde ?", "Who was on watch?"),
    ("Yann, comme tous les jeudis.", "Yann, like every Thursday."),
    ("Et personne ne l'a vu depuis ?", "And nobody has seen him since?"),
    ("Sa barque est encore au port.", "His boat is still in the harbour."),
    ("Alors il n'est pas parti en mer.", "Then he didn't go out to sea."),
    ("Il faut prévenir la capitainerie.", "We have to tell the harbour office."),
    ("Ils ne feront rien avant demain.", "They won't do anything before tomorrow."),
    ("Le vent se lève.", "The wind is picking up."),
    ("Rentrons avant la tempête.", "Let's get back before the storm."),
    ("Tu as entendu ça ?", "Did you hear that?"),
    ("C'est la corne de brume.", "It's the foghorn."),
    ("À cette heure-ci ?", "At this hour?"),
    ("Quelqu'un est monté là-haut.", "Someone went up there."),
    ("La porte était fermée à clé.", "The door was locked."),
    ("Yann avait la seule clé.", "Yann had the only key."),
]
THOUGHTS = [
    "(Il ne reviendra pas.)",
    "(Pas encore une fois.)",
    "(Je savais qu'il mentait.)",
]
DASHES = [
    ("Tu viens avec moi ?", "Pas sous cette pluie."),
    ("Tu l'as vu ?", "Non, pas depuis hier."),
]
SIGNS = ["PHARE DE KERVEN", "CAPITAINERIE", "ENTRÉE INTERDITE"]

STYLES = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,58,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,2,30,30,40,1
Style: Pensées,Arial,58,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,1,0,0,100,100,0,0,1,1.5,0,2,30,30,40,1
Style: Dialogue à deux,Arial,58,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,1,30,30,40,1
Style: Panneaux,Verdana,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,8,10,10,10,1
"""

# Each episode's audio and subtitle tracks: (language, kind, title, forced).
EPISODES = {
    f"{SERIES} - S01E01.mkv": (
        "eng",
        [
            ("fre", "full", "VOSTFR", False),
            ("fre", "signs", "Panneaux", True),
            ("eng", "srt", "English", False),
        ],
    ),
    f"{SERIES} - S01E02.mkv": (
        "eng",
        [("fre", "frsrt", "Français", False), ("eng", "srt", "English", False)],
    ),
    f"{SERIES} - S01E03.mkv": (
        "fre",
        [
            ("fre", "full", "VF", False),
            ("fre", "signs", "Forcés", True),
            ("eng", "srt", "English", False),
        ],
    ),
    f"{SERIES} - Bonus.mkv": ("eng", []),
}


def srt(path: Path, lines: list[tuple[float, str]]) -> None:
    blocks = [
        f"{i + 1}\n{ts(a, ',', 3)} --> {ts(a + STEP - 0.5, ',', 3)}\n{text}\n"
        for i, (a, text) in enumerate(lines)
    ]
    path.write_text("\n".join(blocks), encoding="utf-8")


def ass(path: Path, events: list[tuple[float, str, str]]) -> None:
    dialogue = "\n".join(
        f"Dialogue: 0,{ts(a, '.', 2)},{ts(a + STEP - 0.5, '.', 2)},{style},,0,0,0,,{text}"
        for a, style, text in events
    )
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n"
        + STYLES
        + "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + dialogue
        + "\n",
        encoding="utf-8",
    )


def write_subtitle(path: Path, kind: str) -> None:
    times = [float(t) for t in range(2, DURATION - STEP, STEP)]
    if kind == "srt":
        srt(path, [(t, LINES[i % len(LINES)][1]) for i, t in enumerate(times)])
    elif kind == "frsrt":
        srt(
            path,
            [
                (
                    t,
                    LINES[i % len(LINES)][0]
                    if i % 9
                    else f"<i>{THOUGHTS[i % len(THOUGHTS)]}</i>",
                )
                for i, t in enumerate(times)
            ],
        )
    elif kind == "signs":
        ass(
            path,
            [
                (t, "Panneaux", f"{{\\pos(960,180)}}{SIGNS[i % len(SIGNS)]}")
                for i, t in enumerate(times[::40])
            ],
        )
    else:
        events = []
        for i, t in enumerate(times):
            if i % 40 == 0:
                events.append(
                    (t, "Panneaux", f"{{\\pos(960,180)}}{SIGNS[i // 40 % len(SIGNS)]}")
                )
            if i % 9 == 4:
                events.append((t, "Pensées", THOUGHTS[i % len(THOUGHTS)]))
            elif i % 13 == 6:
                a, b = DASHES[i % len(DASHES)]
                events.append((t, "Dialogue à deux", f"– {a}\\N– {b}"))
            else:
                events.append((t, "Default", LINES[i % len(LINES)][0]))
        ass(path, events)


def make(out_dir: Path, name: str, audio: str, subtitles: list, tmp: Path) -> None:
    inputs = [
        *("-f", "lavfi", "-i", f"color=c=0x203048:s=1920x1080:r=5:d={DURATION}"),
        *("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono"),
    ]
    maps = ["-map", "0:v", "-map", "1:a"]
    meta = ["-metadata:s:a:0", f"language={audio}", "-disposition:a:0", "default"]
    for i, (language, kind, title, forced) in enumerate(subtitles):
        sub = tmp / f"{name}-{i}.{'srt' if 'srt' in kind else 'ass'}"
        write_subtitle(sub, kind)
        inputs += ["-i", str(sub)]
        maps += ["-map", f"{i + 2}:s"]
        meta += [
            f"-metadata:s:s:{i}",
            f"language={language}",
            f"-metadata:s:s:{i}",
            f"title={title}",
        ]
        meta += [f"-disposition:s:{i}", "forced" if forced else "0"]
    codecs = [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "40",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-c:s",
        "copy",
    ]
    cmd = [
        resolve_ffmpeg(),
        "-v",
        "error",
        "-y",
        *inputs,
        *maps,
        *codecs,
        *meta,
        "-t",
        str(DURATION),
        str(out_dir / name),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    out_dir = (
        (
            Path(sys.argv[1])
            if len(sys.argv) > 1
            else Path(__file__).parent / "media" / "demo"
        )
        / SERIES
        / "Saison 1"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).parent
    stamp = hashlib.sha256(
        (here / "make_demo.py").read_bytes() + (here / "make_media.py").read_bytes()
    ).hexdigest()
    stamp_file = out_dir / "stamp.txt"
    if (
        stamp_file.exists()
        and stamp_file.read_text() == stamp
        and all((out_dir / n).exists() for n in EPISODES)
    ):
        print(f"demo up to date in {out_dir}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        for name, (audio, subtitles) in EPISODES.items():
            make(out_dir, name, audio, subtitles, Path(tmp))
            print(f"made {name}")
    stamp_file.write_text(stamp)


if __name__ == "__main__":
    main()
