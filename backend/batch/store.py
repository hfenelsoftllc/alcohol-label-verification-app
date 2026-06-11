"""In-memory batch job store (ISSUE 3.1).

A process-local dict keyed by job_id, cleared on restart. `orchestrator.
start_batch` reads and mutates the `Job` records created here as it
processes each label. FedRAMP SI-12 (Information Management and Retention)
— job state is retained only for the session/process lifetime.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models import ApplicationData, JobState, VerificationResult


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


_JOBS: dict[str, Job] = {}


def create_job(total: int) -> Job:
    job = Job(job_id=secrets.token_urlsafe(12), total=total)
    _JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _JOBS.get(job_id)


def clear() -> None:
    """Test helper — drop all jobs."""
    _JOBS.clear()
