"""In-memory batch job store (ISSUE 3.1).

A process-local dict keyed by job_id, cleared on restart. `orchestrator.
start_batch` reads and mutates the `Job` records created here as it
processes each label. FedRAMP SI-12 (Information Management and Retention)
— job state is retained only for the session/process lifetime, and each
job (the reviewer's "session") is reaped after `SESSION_TTL_SECONDS` of
inactivity (ISSUE 3.5).
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app import redis_client
from app.audit import log_session_expired
from app.models import ApplicationData, JobState, VerificationResult

#: How long an idle job is kept before being reaped. Configurable via
#: SESSION_TTL_HOURS (default 4 — see .env.example).
SESSION_TTL_SECONDS: float = float(os.getenv("SESSION_TTL_HOURS", "4")) * 3600


@dataclass
class LabelInput:
    """One label image plus the application data to verify it against."""

    image_bytes: bytes
    application_data: ApplicationData
    filename: str | None = None


@dataclass
class Job:
    job_id: str
    #: Auth session that created this job (ISSUE 3.7) — `/jobs/*` routes
    #: only serve a job to the session that owns it.
    session_id: str
    total: int
    state: JobState = JobState.PENDING
    completed: int = 0
    # `None` placeholders mark labels not yet processed, so an SSE stream can
    # tell which indices are done without waiting for the whole batch.
    results: list[VerificationResult | None] = field(default_factory=list)
    labels: list[LabelInput] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_JOBS: dict[str, Job] = {}


def _is_expired(job: Job, now: datetime) -> bool:
    return (now - job.last_accessed).total_seconds() > SESSION_TTL_SECONDS


def _reap_expired() -> None:
    """Drop jobs idle longer than SESSION_TTL_SECONDS, logging each (SI-12)."""
    now = datetime.now(timezone.utc)
    expired = [job_id for job_id, job in _JOBS.items() if _is_expired(job, now)]
    for job_id in expired:
        del _JOBS[job_id]
        log_session_expired(session_id=job_id)


def _label_to_dict(label: LabelInput) -> dict:
    return {
        "image_bytes": base64.b64encode(label.image_bytes).decode("ascii"),
        "application_data": label.application_data.model_dump(mode="json"),
        "filename": label.filename,
    }


def _label_from_dict(data: dict) -> LabelInput:
    return LabelInput(
        image_bytes=base64.b64decode(data["image_bytes"]),
        application_data=ApplicationData.model_validate(data["application_data"]),
        filename=data["filename"],
    )


def _job_to_dict(job: Job) -> dict:
    return {
        "job_id": job.job_id,
        "session_id": job.session_id,
        "total": job.total,
        "state": job.state.value,
        "completed": job.completed,
        "results": [result.model_dump(mode="json") if result is not None else None for result in job.results],
        "labels": [_label_to_dict(label) for label in job.labels],
        "created_at": job.created_at.isoformat(),
        "last_accessed": job.last_accessed.isoformat(),
    }


def _job_from_dict(data: dict) -> Job:
    return Job(
        job_id=data["job_id"],
        session_id=data["session_id"],
        total=data["total"],
        state=JobState(data["state"]),
        completed=data["completed"],
        results=[VerificationResult.model_validate(result) if result is not None else None for result in data["results"]],
        labels=[_label_from_dict(label) for label in data["labels"]],
        created_at=datetime.fromisoformat(data["created_at"]),
        last_accessed=datetime.fromisoformat(data["last_accessed"]),
    )


def save_job(job: Job) -> None:
    """Persist `job`'s current state to Redis (no-op in in-memory mode).

    Called by the orchestrator as it progresses a job, so a `get_job` from a
    different serverless invocation (Vercel) sees up-to-date results.
    """
    if redis_client.client is None:
        return
    redis_client.client.setex(f"job:{job.job_id}", int(SESSION_TTL_SECONDS), json.dumps(_job_to_dict(job)))


def create_job(total: int, session_id: str) -> Job:
    job = Job(job_id=secrets.token_urlsafe(12), session_id=session_id, total=total)
    if redis_client.client is not None:
        save_job(job)
        return job
    _reap_expired()
    _JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    """Look up a job, reaping (and returning None for) one that has expired."""
    if redis_client.client is not None:
        data = redis_client.client.get(f"job:{job_id}")
        if data is None:
            return None
        job = _job_from_dict(json.loads(data))
        job.last_accessed = datetime.now(timezone.utc)
        save_job(job)
        return job

    job = _JOBS.get(job_id)
    if job is None:
        return None
    if _is_expired(job, datetime.now(timezone.utc)):
        del _JOBS[job_id]
        log_session_expired(session_id=job_id)
        return None
    job.last_accessed = datetime.now(timezone.utc)
    return job


def clear() -> None:
    """Test helper — drop all jobs."""
    if redis_client.client is not None:
        redis_client.delete_by_prefix("job:")
        return
    _JOBS.clear()
