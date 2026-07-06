import queue
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from watchless_app.config import JOB_RETENTION_LIMIT
from watchless_app.errors import AppError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class SummaryJob:
    id: str
    url: str
    requested_model: str
    status: str = "queued"
    progress: int = 0
    message: str = "Waiting in queue..."
    title: str = ""
    summary: str = ""
    model: str = ""
    tokens_per_second: float | None = None
    completion_tokens: int | None = None
    elapsed_seconds: float | None = None
    error: str = ""
    error_type: str = ""
    history_id: str = ""
    language: str = ""
    created_at: str = ""
    updated_at: str = ""


class SummaryJobQueue:
    def __init__(self, summarizer):
        self.summarizer = summarizer
        self._queue = queue.Queue()
        self._jobs: dict[str, SummaryJob] = {}
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._work, daemon=True)
        self._worker.start()

    def submit(self, url: str, requested_model: str = "", title: str = "") -> SummaryJob:
        if not (url or "").strip():
            raise AppError("Paste at least one YouTube URL first.", "missing_url")
        job = SummaryJob(
            id=uuid.uuid4().hex,
            url=url.strip(),
            requested_model=(requested_model or "").strip(),
            title=(title or "").strip(),
            created_at=_now(),
            updated_at=_now(),
        )
        with self._lock:
            self._jobs[job.id] = job
            self._prune_locked()
        self._queue.put(job.id)
        return job

    def get(self, job_id: str) -> SummaryJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[SummaryJob]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    def _update(self, job_id: str, **changes) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = _now()

    def _progress(self, job_id: str):
        def update(progress: int, message: str, **changes) -> None:
            self._update(job_id, progress=progress, message=message, **changes)
        return update

    def _work(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._run_job(job_id)
            finally:
                self._queue.task_done()

    def _run_job(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        self._update(job_id, status="running", progress=5, message="Starting summary...")
        try:
            result = self.summarizer.summarize(
                job.url,
                job.requested_model,
                progress=self._progress(job_id),
            )
            self._update(
                job_id,
                status="succeeded",
                progress=100,
                message="Summary ready.",
                title=result["title"],
                summary=result["summary"],
                model=result["model"],
                tokens_per_second=result.get("tokens_per_second"),
                completion_tokens=result.get("completion_tokens"),
                elapsed_seconds=result.get("elapsed_seconds"),
                history_id=result["history"]["id"],
                language=result.get("transcript", {}).get("language") or "",
            )
        except AppError as exc:
            self._update(
                job_id,
                status="failed",
                progress=100,
                message=exc.message,
                error=exc.message,
                error_type=exc.error_type,
            )
        except Exception as exc:
            self._update(
                job_id,
                status="failed",
                progress=100,
                message="Unexpected app error.",
                error=f"Unexpected app error: {exc}",
                error_type="unexpected_error",
            )

    def _prune_locked(self) -> None:
        jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
        for stale in jobs[JOB_RETENTION_LIMIT:]:
            self._jobs.pop(stale.id, None)


def serialize_job(job: SummaryJob) -> dict:
    return asdict(job)
