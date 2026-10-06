from __future__ import annotations

import sys

import click

from bobinestyle.ffmpeg_backend import FFmpegError, main_video, probe_streams, subtitle_streams
from bobinestyle.scale import screen_scale


def _fail(message: str) -> None:
    click.echo(f"Erreur : {message}", err=True)
    sys.exit(1)


@click.group()
def main() -> None:
    """Applique le style maison aux sous-titres français d'un MKV."""
    # Windows consoles default to cp1252: accented titles would crash echo.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
def probe(file: str) -> None:
    """Affiche la vidéo, les pistes de sous-titres et les polices d'un fichier."""
    try:
        streams = probe_streams(file)
    except FFmpegError as exc:
        _fail(str(exc))

    video = main_video(streams)
    if video is None:
        click.echo("Vidéo : aucune (échelle de référence 1080p)")
    else:
        width, height = video.display_size
        stored = "" if (width, height) == (video.width, video.height) else f" (stockée {video.width}x{video.height})"
        click.echo(f"Vidéo : {width}x{height}{stored}   échelle du style x{screen_scale(width, height):.3f}")

    subs = subtitle_streams(streams)
    click.echo(f"{len(subs)} piste(s) de sous-titres :")
    for s in subs:
        flags = [f for f, on in (("défaut", s.default), ("forcés", s.forced)) if on]
        click.echo(f"  @{s.index}  {s.codec:<8} {s.language or '-':<5} {s.title or '':<30} {' '.join(flags)}".rstrip())

    fonts = [s.filename or "?" for s in streams if s.kind == "Attachment"]
    if fonts:
        click.echo(f"Pièces jointes : {', '.join(fonts)}")
