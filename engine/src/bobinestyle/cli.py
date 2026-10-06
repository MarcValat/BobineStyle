from __future__ import annotations

import sys
import threading
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
from bobinestyle.batch import FileResult, Status, run_batch, summary
from bobinestyle.mux import FRENCH_CODES, MuxError, MuxPlan, default_output, mux, plan
from bobinestyle.roles import ScriptReport, analyze
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
        click.echo(f"  {name:<24} -> {role.label}")
    for warning in result.warnings:
        click.echo(f"⚠ {warning}")
    click.echo(f"Écrit : {out}")


@main.command("mux")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "-o", type=click.Path(dir_okay=False), help="MKV écrit (Output/<même nom> par défaut).")
@click.option("--plan", "plan_only", is_flag=True, help="Affiche ce qui serait fait, sans rien écrire.")
def mux_command(file: str, output: str | None, plan_only: bool) -> None:
    """Remuxe le MKV avec ses sous-titres français au style maison et les polices jointes."""
    try:
        p = plan(file)
    except FFmpegError as exc:
        _fail(str(exc))
    _echo_plan(p)
    if not any(t.french for t in p.tracks):
        _fail("aucune piste de sous-titres française")
    if plan_only:
        return
    target = Path(output) if output else default_output(file)
    try:
        written = mux(p, target)
    except MuxError as exc:
        _fail(str(exc))
    click.echo(f"Écrit et vérifié : {written}")


def _echo_plan(p: MuxPlan, indent: str = "") -> None:
    if p.audio is None:
        click.echo(indent + "Pas d'audio : sous-titres complets par défaut")
    else:
        lang = p.audio.language or "langue inconnue"
        choice = "forcés" if p.audio.language in FRENCH_CODES else "complets"
        click.echo(f"{indent}Audio par défaut : {lang} {p.audio.title or ''}".rstrip() + f"  ->  sous-titres {choice} par défaut")
    for t in p.tracks:
        s = t.stream
        if t.french:
            flags = " ".join(f for f, on in (("défaut", t.default), ("forcés", t.forced)) if on)
            action = "restylé" if t.text is not None else "copié"
            lines = f"{t.dialogue_lines} répliques" if t.dialogue_lines is not None else "?"
            click.echo(f"{indent}@{s.index}  {s.title or '-'}  ->  {t.title}  {flags}  ({action}, {lines})")
        else:
            click.echo(f"{indent}@{s.index}  {s.language or '-'} {s.title or ''}  ->  inchangé".rstrip())
        for note in t.notes:
            click.echo(f"{indent}      {note}")
    if p.fonts:
        click.echo(f"{indent}Polices jointes : {', '.join(f.path.name for f in p.fonts)}")
    if p.fonts_present:
        click.echo(f"{indent}Déjà dans le MKV : {', '.join(p.fonts_present)}")
    for warning in p.warnings:
        click.echo(f"{indent}⚠ {warning}")


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--output", "-o", type=click.Path(file_okay=False), help="Dossier de sortie (<dossier>/Output par défaut).")
@click.option("--recursive", "-r", is_flag=True, help="Inclut les sous-dossiers (saisons).")
@click.option("--jobs", "-j", type=click.IntRange(1, 8), default=2, show_default=True, help="Fichiers traités en parallèle.")
@click.option("--plan", "plan_only", is_flag=True, help="Affiche ce qui serait fait, sans rien écrire.")
@click.option("--force", is_flag=True, help="Refait les fichiers déjà présents dans le dossier de sortie.")
@click.option("--details", is_flag=True, help="Affiche le détail des pistes de chaque fichier.")
def batch(folder: str, output: str | None, recursive: bool, jobs: int, plan_only: bool, force: bool, details: bool) -> None:
    """Traite tous les MKV d'un dossier."""
    root = Path(folder)
    lock = threading.Lock()

    def report(r: FileResult) -> None:
        name = str(r.source.relative_to(root))
        with lock:
            if r.status is Status.ERROR:
                click.echo(f"✗ {name} : {r.error.splitlines()[-1] if r.error else 'erreur'}")
            elif r.status is Status.EXISTS:
                click.echo(f"= {name} : déjà dans la sortie")
            elif r.status is Status.NO_FRENCH:
                click.echo(f"- {name} : pas de sous-titres français")
            else:
                french = sum(t.french for t in r.plan.tracks)
                mark = "✓" if r.status is Status.DONE else "?"
                click.echo(f"{mark} {name} : {french} piste(s) FR, {len(r.plan.fonts)} police(s) jointe(s)")
            if details and r.plan and r.status in (Status.DONE, Status.PLANNED):
                _echo_plan(r.plan, indent="    ")

    results = run_batch(
        root, Path(output) if output else None, recursive, jobs, plan_only, force, on_result=report
    )
    if not results:
        _fail("aucun fichier MKV dans ce dossier")
    labels = {
        Status.DONE: "traité(s)",
        Status.PLANNED: "à traiter",
        Status.EXISTS: "déjà fait(s)",
        Status.NO_FRENCH: "sans sous-titres français",
        Status.ERROR: "en erreur",
    }
    click.echo("Bilan : " + ", ".join(f"{n} {labels[status]}" for status, n in summary(results)))
    if any(r.status is Status.ERROR for r in results):
        sys.exit(1)


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
            f"  {r.style.name[:24]:<24} {r.role.label:<16} {r.lines:>6} {r.dialogue_lines:>8}  "
            f"{', '.join(r.reasons)}".rstrip()
        )
