"""Tests for degrading to the in-process store when Redis is configured but
unreachable (ISSUE 4.8) — a misconfigured or unreachable REDIS_URL must not
crash every request, only degrade session/job persistence.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app import redis_client, session
from app.main import app
from batch import store


def test_session_create_falls_back_when_redis_unavailable(monkeypatch):
    session.clear()
    fake_redis = MagicMock()
    fake_redis.setex.side_effect = RedisError("boom")
    monkeypatch.setattr(redis_client, "client", fake_redis)

    created = session.create()

    assert created.session_id in session._SESSIONS


def test_session_validate_cookie_falls_back_when_redis_unavailable(monkeypatch):
    session.clear()
    existing = session.Session(session_id="existing-session-id")
    session._SESSIONS[existing.session_id] = existing
    token = session.sign(existing.session_id)

    fake_redis = MagicMock()
    fake_redis.get.side_effect = RedisError("boom")
    monkeypatch.setattr(redis_client, "client", fake_redis)

    assert session.validate_cookie(token) == existing.session_id


def test_batch_save_job_falls_back_when_redis_unavailable(monkeypatch):
    store.clear()
    job = store.Job(job_id="job-1", session_id="s1", total=1)

    fake_redis = MagicMock()
    fake_redis.setex.side_effect = RedisError("boom")
    monkeypatch.setattr(redis_client, "client", fake_redis)

    store.save_job(job)

    assert store._JOBS["job-1"] is job


def test_batch_get_job_falls_back_when_redis_unavailable(monkeypatch):
    store.clear()
    job = store.Job(job_id="job-2", session_id="s1", total=1)
    store._JOBS[job.job_id] = job

    fake_redis = MagicMock()
    fake_redis.get.side_effect = RedisError("boom")
    monkeypatch.setattr(redis_client, "client", fake_redis)

    fetched = store.get_job(job.job_id)

    assert fetched is not None
    assert fetched.job_id == job.job_id


def test_health_endpoint_does_not_500_when_redis_unavailable(monkeypatch):
    """Reproduces the production outage: every request minted a session via
    `session.create()`, which raised when Redis was unreachable."""
    session.clear()
    fake_redis = MagicMock()
    fake_redis.setex.side_effect = RedisError("boom")
    monkeypatch.setattr(redis_client, "client", fake_redis)

    fresh = TestClient(app, base_url="https://testserver")
    resp = fresh.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
