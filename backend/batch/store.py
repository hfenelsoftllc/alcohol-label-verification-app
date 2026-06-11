"""In-memory batch job store (ISSUE 3.1).

A process-local dict keyed by job_id, cleared on restart. `orchestrator.
start_batch` reads and mutates the `Job` records created here as it
processes each label. FedRAMP SI-12 (Information Management and Retention)
— job state is retained only for the session/process lifetime, and each
job (the reviewer's "session") is reaped after `SESSION_TTL_SECONDS` of
inactivity (ISSUE 3.5).
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

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


def create_job(total: int) -> Job:
    _reap_expired()
    job = Job(job_id=secrets.token_urlsafe(12), total=total)
    _JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    """Look up a job, reaping (and returning None for) one that has expired."""
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
    _JOBS.clear()
