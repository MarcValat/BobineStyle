"""A minimal in-memory background job registry, for progress-tracked long operations.

Each job runs its target function in its own thread; the function receives a
``log`` callback appending to a lock-protected message list, and a
``progress`` callback (0 to 1). A WebSocket handler polls both and streams
what changed to the client. There's no message broker or
persistence: this is a single-process local sidecar, not a distributed
system, and jobs are lost on restart -- acceptable for a tool a person is
actively watching run.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from bobinestyle.cancellation import Cancelled, bind_cancel_event

JobStatus = Literal["running", "done", "error", "cancelled"]


@dataclass
class Job:
    id: str
    status: JobStatus = "running"
    messages: list[str] = field(default_factory=list)
    progress: float | None = None
    result: Any = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # Set to stop the job: its ffmpeg runs watch it (see cancellation.py).
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def cancel(self) -> None:
        """Ask the job to stop; it ends as "cancelled" shortly after."""
        self._cancel.set()

    def log(self, message: str) -> None:
        with self._lock:
            self.messages.append(message)

    def set_progress(self, fraction: float) -> None:
        with self._lock:
            self.progress = max(0.0, min(1.0, fraction))

    def snapshot(self, since: int = 0) -> tuple[list[str], int, float | None, JobStatus, Any, str | None]:
        """New messages since index ``since``, the new cursor, and the job's current state."""
        with self._lock:
            return (
                list(self.messages[since:]), len(self.messages), self.progress, self.status, self.result, self.error
            )

    def finish(self, result: Any) -> None:
        with self._lock:
            self.result = result
            self.status = "done"

    def fail(self, error: str) -> None:
        with self._lock:
            self.error = error
            self.status = "error"

    def mark_cancelled(self) -> None:
        with self._lock:
            self.status = "cancelled"


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()


def start_job(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Job:
    """Run ``fn(*args, log=job.log, progress=job.set_progress, **kwargs)`` in a
    background thread; return its ``Job`` immediately."""
    job = Job(id=uuid.uuid4().hex)
    with _jobs_lock:
        _jobs[job.id] = job

    def runner() -> None:
        bind_cancel_event(job._cancel)
        try:
            result = fn(*args, log=job.log, progress=job.set_progress, **kwargs)
            job.finish(result)
        except Cancelled:
            job.mark_cancelled()
        except Exception as exc:  # noqa: BLE001 - a background thread has no other way to surface a failure
            # An HTTPException's str() is "400: <detail>"; the user only needs the detail.
            job.fail(str(getattr(exc, "detail", None) or exc))

    threading.Thread(target=runner, daemon=True).start()
    return job


def get_job(job_id: str) -> Job | None:
    with _jobs_lock:
        return _jobs.get(job_id)
