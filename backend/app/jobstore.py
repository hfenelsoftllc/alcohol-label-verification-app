"""In-memory batch job store.

Phase 1 stub: a process-local dict keyed by job_id, cleared on restart. The real
async orchestrator (ISSUE 3.1) and session-scoped store with TTL expiry
(ISSUE 3.5) replace this. Kept deliberately tiny so it is easy to swap out.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models import JobState, VerificationResult


@dataclass
class Job:
    job_id: str
    total: int
    state: JobState = JobState.PENDING
    completed: int = 0
    results: list[VerificationResult] = field(default_factory=list)
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
