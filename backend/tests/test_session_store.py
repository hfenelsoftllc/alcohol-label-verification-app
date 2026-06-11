"""Unit tests for the in-memory job/session store and TTL expiry (ISSUE 3.5).

FedRAMP SI-12 (Information Management and Retention) — a job ("session") is
reaped after `SESSION_TTL_SECONDS` of inactivity, with no disk writes
(SC-28, Protection of Information at Rest).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from batch import store


def _events(raw: str) -> list[dict]:
    events = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def test_create_job_sets_created_and_last_accessed():
    store.clear()
    before = datetime.now(timezone.utc)

    job = store.create_job(total=3)

    assert before <= job.created_at <= datetime.now(timezone.utc)
    assert abs((job.last_accessed - job.created_at).total_seconds()) < 1
    assert job.total == 3


def test_get_job_refreshes_last_accessed():
    store.clear()
    job = store.create_job(total=1)
    job.last_accessed = datetime.now(timezone.utc) - timedelta(seconds=1)
    stale = job.last_accessed

    fetched = store.get_job(job.job_id)

    assert fetched is not None
    assert fetched.last_accessed > stale


def test_job_within_ttl_is_not_reaped():
    store.clear()
    job = store.create_job(total=1)
    job.last_accessed = datetime.now(timezone.utc) - timedelta(seconds=store.SESSION_TTL_SECONDS - 1)

    assert store.get_job(job.job_id) is not None


def test_get_job_reaps_expired_session_and_logs(capsys):
    store.clear()
    job = store.create_job(total=1)
    job.last_accessed = datetime.now(timezone.utc) - timedelta(seconds=store.SESSION_TTL_SECONDS + 1)

    assert store.get_job(job.job_id) is None

    expired = next(e for e in _events(capsys.readouterr().out) if e["event"] == "session_expired")
    assert expired["session_id"] == job.job_id


def test_create_job_sweeps_expired_sessions(capsys):
    store.clear()
    stale = store.create_job(total=1)
    stale.last_accessed = datetime.now(timezone.utc) - timedelta(seconds=store.SESSION_TTL_SECONDS + 1)

    fresh = store.create_job(total=1)

    assert store.get_job(stale.job_id) is None
    assert store.get_job(fresh.job_id) is not None

    expired_ids = {e["session_id"] for e in _events(capsys.readouterr().out) if e["event"] == "session_expired"}
    assert stale.job_id in expired_ids
