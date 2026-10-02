"""Integration tests against a real Redis instance (ISSUE 4.8).

Unlike `tests/test_redis_fallback.py` (which mocks `RedisError` to test the
fallback logic in isolation), these tests exercise the actual redis-py client
against a real Redis server — confirming both normal round-tripping and that
a genuine connection failure (not a mocked one) is caught by the
`except RedisError` fallback in `app/session.py` and `batch/store.py`.

Skipped automatically unless `TEST_REDIS_URL` is explicitly set — CI sets it
to the `redis` service container in `.github/workflows/ci.yml`. This is
deliberately opt-in rather than guessing a default host/port: a dev machine
commonly has some unrelated Redis already listening on 6379 for a different
project, and these tests `flushdb()` whatever they connect to.

`REDIS_URL` is deliberately not read here — that env var drives
`app.redis_client`'s module-level singleton for the *whole* test session,
and several existing tests simulate TTL expiry by mutating a Job/Session
object directly, which only works against the in-memory store. Each test
below instead monkeypatches `redis_client.client` for just its own scope, so
the rest of the suite is unaffected.
"""

from __future__ import annotations

import os

import pytest
import redis as redis_lib
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app import redis_client, session
from app.main import app
from batch import store

_TEST_REDIS_URL = os.getenv("TEST_REDIS_URL")


@pytest.fixture
def real_redis(monkeypatch):
    """Point `redis_client.client` at a real, reachable Redis for one test.

    Skips (rather than fails) when `TEST_REDIS_URL` isn't set or isn't
    reachable, so this file is a no-op in local dev without it configured.
    """
    if not _TEST_REDIS_URL:
        pytest.skip("TEST_REDIS_URL not set — skipping real-Redis integration tests")

    client = redis_lib.Redis.from_url(_TEST_REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    try:
        client.ping()
    except RedisError:
        pytest.skip(f"no Redis reachable at {_TEST_REDIS_URL}")

    client.flushdb()
    monkeypatch.setattr(redis_client, "client", client)
    yield client
    client.flushdb()


@pytest.fixture
def unreachable_redis(monkeypatch):
    """Point `redis_client.client` at a real `redis.Redis` whose connection
    genuinely fails, to confirm the fallback catches what redis-py actually
    raises rather than only a mocked `RedisError`.

    Clears the stores *before* patching — `session.clear()`/`store.clear()`
    are test-only helpers with no fallback of their own, so they must run
    while `redis_client.client` is still in its normal (unpatched) state.
    """
    session.clear()
    store.clear()
    # Port 1 is reserved/unassigned; nothing listens there, so this fails
    # fast with a real ConnectionError instead of a mock.
    client = redis_lib.Redis.from_url("redis://localhost:1/0", socket_connect_timeout=1, socket_timeout=1)
    monkeypatch.setattr(redis_client, "client", client)
    return client


def test_session_round_trips_through_real_redis(real_redis):
    session.clear()

    created = session.create()

    assert real_redis.get(f"session:{created.session_id}") is not None
    assert session.validate_cookie(session.sign(created.session_id)) == created.session_id


def test_job_round_trips_through_real_redis(real_redis):
    store.clear()

    job = store.create_job(total=2, session_id="test-session")
    fetched = store.get_job(job.job_id)

    assert fetched is not None
    assert fetched.job_id == job.job_id
    assert fetched.total == 2
    assert fetched.session_id == "test-session"


def test_session_create_falls_back_on_real_connection_failure(unreachable_redis):
    created = session.create()

    assert created.session_id in session._SESSIONS


def test_batch_save_job_falls_back_on_real_connection_failure(unreachable_redis):
    job = store.Job(job_id="real-fail-job", session_id="s1", total=1)

    store.save_job(job)

    assert store._JOBS["real-fail-job"] is job


def test_health_endpoint_does_not_500_with_real_connection_failure(unreachable_redis):
    fresh = TestClient(app, base_url="https://testserver")

    resp = fresh.get("/health")

    assert resp.status_code == 200
