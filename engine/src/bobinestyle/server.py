"""HTTP sidecar exposing the engine to the app.

Quick requests (expanding dropped paths, planning a file, output paths)
answer directly. Remuxes run as jobs: ``POST /jobs/mux`` returns a
``job_id`` at once, and ``WS /jobs/{job_id}/ws`` streams the job's
messages and progress, ending with its result, its error or its
cancellation.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bobinestyle import __version__
from bobinestyle.batch import OUTPUT_DIR, find_videos
from bobinestyle.ffmpeg_backend import FFmpegError
from bobinestyle.fonts import system_fonts
from bobinestyle.jobs import get_job, start_job
from bobinestyle.mux import FRENCH_CODES, MuxError, MuxPlan, default_output, mux, plan

app = FastAPI(title="Bobine Style", version=__version__)

# Only ever bound to 127.0.0.1 (see `bobinestyle serve`): open CORS just
# lets the app's webview (tauri://..., localhost:1420 in dev) call it.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Index the system fonts while the app starts, not on the first file.
threading.Thread(target=system_fonts, daemon=True).start()


@app.exception_handler(FFmpegError)
@app.exception_handler(MuxError)
async def _engine_error(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


# --- files -------------------------------------------------------------------


class ExpandRequest(BaseModel):
    paths: list[str]
    recursive: bool = False


@app.post("/paths/expand")
def expand_paths(req: ExpandRequest) -> dict[str, list[str]]:
    """Dropped or picked paths as MKV files: a file as is, a folder as its
    MKVs in name order (its seasons too when ``recursive``), never what a
    previous run wrote into its Output folder."""
    files: list[str] = []
    for path in map(Path, req.paths):
        if path.is_dir():
            files += [str(f) for f in find_videos(path, req.recursive, path / OUTPUT_DIR)]
        elif path.is_file() and path.suffix.lower() == ".mkv" and not path.name.endswith(".part.mkv"):
            files.append(str(path))
    return {"files": list(dict.fromkeys(files))}


class OutputsRequest(BaseModel):
    sources: list[str]
    folder: str | None = None


class OutputModel(BaseModel):
    path: str
    exists: bool


@app.post("/outputs")
def outputs(req: OutputsRequest) -> dict[str, list[OutputModel]]:
    """Where each file goes: ``Output/<name>`` next to it, or ``folder/<name>``
    (``folder/<its folder>/<name>`` when two sources share a name, as
    episodes of different seasons do), and whether something is there."""
    if req.folder is None:
        paths = [default_output(s) for s in req.sources]
    else:
        names = [Path(s).name.lower() for s in req.sources]
        paths = []
        for source, name in zip(req.sources, names):
            path = Path(source)
            shared = names.count(name) > 1
            paths.append(Path(req.folder) / path.parent.name / path.name if shared else Path(req.folder) / path.name)
    return {"outputs": [OutputModel(path=str(p), exists=p.exists()) for p in paths]}


@app.get("/exists")
def exists(path: str) -> dict[str, bool]:
    return {"exists": Path(path).exists()}


# --- plan --------------------------------------------------------------------


class TrackModel(BaseModel):
    index: int
    codec: str
    language: str | None
    title: str | None
    french: bool
    # French tracks only.
    kind: str | None
    new_title: str | None
    default: bool
    forced: bool
    action: str  # "restyle", "convert" (SRT -> ASS), "copy"
    dialogue_lines: int | None
    notes: list[str]


class AudioModel(BaseModel):
    language: str | None
    title: str | None
    french: bool


class PlanModel(BaseModel):
    path: str
    video_size: tuple[int, int] | None
    audio: AudioModel | None
    tracks: list[TrackModel]
    fonts: list[str]
    fonts_present: list[str]
    fonts_missing: list[str]
    warnings: list[str]

    @classmethod
    def of(cls, p: MuxPlan) -> PlanModel:
        tracks = []
        for t in p.tracks:
            s = t.stream
            if not t.french or t.text is None:
                action = "copy"
            else:
                action = "convert" if s.codec in ("subrip", "srt") else "restyle"
            tracks.append(
                TrackModel(
                    index=s.index,
                    codec=s.codec,
                    language=s.language,
                    title=s.title,
                    french=t.french,
                    kind=t.kind,
                    new_title=t.title,
                    default=t.default if t.french else s.default and not any(x.default for x in p.tracks if x.french),
                    forced=t.forced if t.french else s.forced,
                    action=action,
                    dialogue_lines=t.dialogue_lines,
                    notes=t.notes,
                )
            )
        audio = None
        if p.audio is not None:
            audio = AudioModel(language=p.audio.language, title=p.audio.title, french=p.audio.language in FRENCH_CODES)
        return cls(
            path=p.source,
            video_size=p.video_size,
            audio=audio,
            tracks=tracks,
            fonts=[f.path.name for f in p.fonts],
            fonts_present=p.fonts_present,
            fonts_missing=p.fonts_missing,
            warnings=p.warnings,
        )


class PlanRequest(BaseModel):
    path: str


@app.post("/plan", response_model=PlanModel)
def plan_file(req: PlanRequest) -> PlanModel:
    """What processing ``path`` would do, without writing anything."""
    if not Path(req.path).is_file():
        raise HTTPException(400, f"Fichier introuvable : {req.path}")
    return PlanModel.of(plan(req.path))


# --- jobs --------------------------------------------------------------------


class JobStarted(BaseModel):
    job_id: str


class MuxRequest(BaseModel):
    source: str
    output: str


@app.post("/jobs/mux", response_model=JobStarted)
def start_mux(req: MuxRequest) -> JobStarted:
    def run(log, progress):
        log("Analyse des pistes…")
        p = plan(req.source)
        if not any(t.french for t in p.tracks):
            raise MuxError("aucune piste de sous-titres française")
        log("Remux…")
        written = mux(p, req.output, progress)
        log(f"Écrit et vérifié : {written}")
        return {"path": str(written), "plan": PlanModel.of(p).model_dump()}

    return JobStarted(job_id=start_job(run).id)


@app.websocket("/jobs/{job_id}/ws")
async def job_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    job = get_job(job_id)
    if job is None:
        await websocket.send_json({"type": "error", "message": f"Tâche inconnue : {job_id}"})
        await websocket.close()
        return
    since = 0
    sent_progress: float | None = None
    try:
        while True:
            messages, since, progress, status, result, error = job.snapshot(since)
            for message in messages:
                await websocket.send_json({"type": "log", "message": message})
            if progress is not None and progress != sent_progress:
                sent_progress = progress
                await websocket.send_json({"type": "progress", "value": progress})
            if status != "running":
                if status == "done":
                    await websocket.send_json({"type": "done", "result": result})
                elif status == "cancelled":
                    await websocket.send_json({"type": "cancelled"})
                else:
                    await websocket.send_json({"type": "error", "message": error})
                break
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return
    await websocket.close()


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, bool]:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, f"Tâche inconnue : {job_id}")
    job.cancel()
    return {"cancelled": True}
