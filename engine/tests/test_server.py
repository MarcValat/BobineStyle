from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bobinestyle.ffmpeg_backend import resolve_ffmpeg, run_checked
from bobinestyle.jobs import start_job
from bobinestyle.server import app
from test_batch import series  # noqa: F401 - fixture
from test_mux import mkv  # noqa: F401 - fixture

client = TestClient(app)


def _events(job_id: str) -> list[dict]:
    with client.websocket_connect(f"/jobs/{job_id}/ws") as ws:
        events = []
        while True:
            events.append(ws.receive_json())
            if events[-1]["type"] in ("done", "error", "cancelled"):
                return events


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_expand_folders_and_files(series: Path):  # noqa: F811
    files = client.post("/paths/expand", json={"paths": [str(series)], "recursive": True}).json()["files"]
    assert [Path(f).relative_to(series).as_posix() for f in files] == [
        "S01/E01.mkv", "S01/E02.mkv", "S02/E01.mkv", "S02/E02.mkv",
    ]
    single = client.post("/paths/expand", json={"paths": [files[0], files[0], str(series / "nope.mkv")]}).json()
    assert single["files"] == [files[0]]
    assert client.post("/paths/expand", json={"paths": [str(series)]}).json()["files"] == []


def test_outputs(series: Path, tmp_path: Path):  # noqa: F811
    sources = [str(series / "S01" / "E01.mkv"), str(series / "S01" / "E02.mkv"), str(series / "S02" / "E01.mkv")]
    default = client.post("/outputs", json={"sources": sources}).json()["outputs"]
    assert default[0] == {"path": str(series / "S01" / "Output" / "E01.mkv"), "exists": False}
    (tmp_path / "E02.mkv").write_bytes(b"")
    folder = client.post("/outputs", json={"sources": sources, "folder": str(tmp_path)}).json()["outputs"]
    assert [(o["path"], o["exists"]) for o in folder] == [
        (str(tmp_path / "S01" / "E01.mkv"), False),
        (str(tmp_path / "E02.mkv"), True),
        (str(tmp_path / "S02" / "E01.mkv"), False),
    ]


def test_plan(mkv: Path):  # noqa: F811
    plan = client.post("/plan", json={"path": str(mkv)}).json()
    english, full, signs = plan["tracks"]
    assert (english["french"], english["action"], english["default"]) == (False, "copy", False)
    assert (full["new_title"], full["action"], full["default"]) == ("Français", "restyle", True)
    assert (signs["kind"], signs["forced"]) == ("forced", True)
    assert client.post("/plan", json={"path": str(mkv) + ".nope"}).status_code == 400


def test_mux_job_reports_progress_and_result(mkv: Path, tmp_path: Path):  # noqa: F811
    output = tmp_path / "out.mkv"
    job_id = client.post("/jobs/mux", json={"source": str(mkv), "output": str(output)}).json()["job_id"]
    events = _events(job_id)
    assert events[-1]["type"] == "done", events
    assert events[-1]["result"]["path"] == str(output)
    assert output.is_file()
    assert any(e["type"] == "progress" for e in events)
    assert [e["message"] for e in events if e["type"] == "log"][0] == "Analyse des pistes…"


def test_mux_job_error(tmp_path: Path):
    broken = tmp_path / "broken.mkv"
    broken.write_bytes(b"not a video")
    job_id = client.post("/jobs/mux", json={"source": str(broken), "output": str(tmp_path / "o.mkv")}).json()["job_id"]
    assert _events(job_id)[-1]["type"] == "error"


def test_cancel_unknown_job():
    assert client.post("/jobs/nope/cancel").status_code == 404


def test_cancel_kills_a_running_ffmpeg():
    """A long ffmpeg run stops within a fraction of a second of the cancel."""
    started = threading.Event()

    def run(log, progress):
        started.set()
        run_checked(
            [resolve_ffmpeg(), "-hide_banner", "-f", "lavfi", "-i", "testsrc=s=640x360:r=25:d=600", "-f", "null", "-"],
            on_size=lambda written: progress(0.0),
        )
        return "finished"

    job = start_job(run)
    started.wait(5)
    time.sleep(0.5)
    begin = time.monotonic()
    assert client.post(f"/jobs/{job.id}/cancel").json() == {"cancelled": True}
    assert _events(job.id)[-1]["type"] == "cancelled"
    assert time.monotonic() - begin < 2


# Who may call the engine (server.TokenGuard, CORS): the app that started it.


@pytest.fixture()
def token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("BOBINESTYLE_TOKEN", "s3cret")
    return "s3cret"


def test_a_request_without_the_token_is_refused(token: str) -> None:
    assert client.get("/exists", params={"path": "x"}).status_code == 401
    assert client.get("/exists", params={"path": "x"}, headers={"X-Bobine-Token": "wrong"}).status_code == 401
    assert client.post("/paths/expand", json={"paths": ["x"]}).status_code == 401


def test_a_request_with_the_token_goes_through(token: str) -> None:
    assert client.get("/exists", params={"path": "x"}, headers={"X-Bobine-Token": token}).status_code == 200


def test_health_answers_without_the_token(token: str) -> None:
    assert client.get("/health").status_code == 200


def test_a_websocket_without_the_token_is_refused(token: str) -> None:
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/jobs/does-not-exist/ws") as ws:
            ws.receive_json()
    with client.websocket_connect(f"/jobs/does-not-exist/ws?token={token}") as ws:
        assert ws.receive_json()["type"] == "error"


def test_no_token_asked_when_none_was_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOBINESTYLE_TOKEN", raising=False)
    assert client.get("/exists", params={"path": "x"}).status_code == 200


@pytest.mark.parametrize("origin", ["tauri://localhost", "http://tauri.localhost", "http://localhost:1420"])
def test_the_app_may_read_the_answers(origin: str) -> None:
    resp = client.get("/health", headers={"Origin": origin})
    assert resp.headers.get("access-control-allow-origin") == origin


def test_a_website_may_not(token: str) -> None:
    resp = client.get("/health", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in resp.headers
    preflight = client.options(
        "/exists",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-bobine-token",
        },
    )
    assert "access-control-allow-origin" not in preflight.headers
