from __future__ import annotations

import sys
from pathlib import Path

import click

from bobinestyle.ass import parse_ass
from bobinestyle.ffmpeg_backend import (
    TEXT_FORMATS,
    FFmpegError,
    extract_subtitle_text,
    main_video,
    probe_streams,
    subtitle_streams,
)
from bobinestyle.roles import Role, ScriptReport, analyze
from bobinestyle.scale import screen_scale
from bobinestyle.style import apply_house_style


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


ROLE_LABELS = {
    Role.DIALOGUE: "dialogue",
    Role.ITALIC: "italique",
    Role.TOP: "haut",
    Role.TOP_ITALIC: "haut italique",
    Role.DASHES: "tirets",
    Role.DASHES_ITALIC: "tirets italique",
    Role.OVERLAP: "overlap",
    Role.MARGINS: "marges",
    Role.TYPESETTING: "typo (inchangé)",
    Role.UNUSED: "inutilisé",
}


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--track", "-t", type=int, help="Numéro de la piste (@N de probe) ; toutes par défaut.")
def inspect(file: str, track: int | None) -> None:
    """Analyse les styles des pistes de sous-titres texte, sans rien modifier."""
    try:
        subs = subtitle_streams(probe_streams(file))
    except FFmpegError as exc:
        _fail(str(exc))
    if track is not None:
        subs = [s for s in subs if s.index == track]
        if not subs:
            _fail(f"pas de piste de sous-titres @{track}")

    for s in subs:
        click.echo(f"\n@{s.index}  {s.codec}  {s.language or '-'}  {s.title or ''}".rstrip())
        if s.codec not in TEXT_FORMATS:
            click.echo("  format image ou non supporté : ignoré")
            continue
        try:
            text = extract_subtitle_text(file, s.index, s.codec)
        except FFmpegError as exc:
            _fail(str(exc))
        if TEXT_FORMATS[s.codec] == "srt":
            count = sum(1 for line in text.splitlines() if "-->" in line)
            click.echo(f"  SRT, {count} répliques : sera converti en ASS au style maison")
            continue
        _echo_report(analyze(parse_ass(text)))


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--track", "-t", type=int, required=True, help="Numéro de la piste ASS (@N de probe).")
@click.option("--output", "-o", type=click.Path(dir_okay=False), help="Fichier .ass écrit (à côté du MKV par défaut).")
def style(file: str, track: int, output: str | None) -> None:
    """Écrit une piste ASS au style maison, adapté à la vidéo."""
    try:
        streams = probe_streams(file)
    except FFmpegError as exc:
        _fail(str(exc))
    sub = next((s for s in subtitle_streams(streams) if s.index == track), None)
    if sub is None:
        _fail(f"pas de piste de sous-titres @{track}")
    if TEXT_FORMATS.get(sub.codec) != "ass":
        _fail(f"la piste @{track} n'est pas en ASS ({sub.codec})")
    video = main_video(streams)
    size = video.display_size if video else None
    try:
        result = apply_house_style(extract_subtitle_text(file, track, sub.codec), size)
    except FFmpegError as exc:
        _fail(str(exc))

    out = Path(output) if output else Path(file).with_suffix(f".{track}.bobine.ass")
    out.write_text(result.text, encoding="utf-8-sig")
    w, h = result.play_res
    click.echo(f"PlayRes {w}x{h} {'(remplacé)' if result.play_res_changed else '(conservé)'}")
    for name, role in result.restyled:
        click.echo(f"  {name:<24} -> {ROLE_LABELS[role]}")
    for warning in result.warnings:
        click.echo(f"⚠ {warning}")
    click.echo(f"Écrit : {out}")


def _echo_report(report: ScriptReport) -> None:
    res = f"{report.play_res[0]}x{report.play_res[1]}" if report.play_res else "absent (384x288)"
    sbas = "oui" if report.scaled_border_and_shadow else "non"
    if report.keep_play_res:
        decision = f"{report.positioned_lines} lignes positionnées : PlayRes conservé"
    else:
        decision = "aucune ligne positionnée : PlayRes remplacé par la taille de la vidéo"
    click.echo(f"  PlayRes {res}   ScaledBorderAndShadow {sbas}")
    click.echo(f"  {decision}")
    click.echo(f"  {'Style':<24} {'Rôle':<16} {'Lignes':>6} {'Dialogue':>8}  Détails")
    for r in report.styles:
        click.echo(
            f"  {r.style.name[:24]:<24} {ROLE_LABELS[r.role]:<16} {r.lines:>6} {r.dialogue_lines:>8}  "
            f"{', '.join(r.reasons)}".rstrip()
        )
