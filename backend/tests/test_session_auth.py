"""Tests for browser session authentication (ISSUE 3.7).

FedRAMP AC-3 (Access Enforcement), IA-2 (Identification and Authentication),
SC-23 (Session Authenticity).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import session
from app.main import app
from tests.test_jobs import _submit_batch


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


def test_first_visit_sets_signed_session_cookie():
    """AC1: a fresh browser receives an HttpOnly/Secure/SameSite=Strict cookie."""
    fresh = TestClient(app, base_url="https://testserver")

    resp = fresh.get("/health")

    assert resp.status_code == 200
    set_cookie = resp.headers["set-cookie"]
    assert set_cookie.startswith(f"{session.COOKIE_NAME}=")
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert re.search(r"SameSite=strict", set_cookie, re.IGNORECASE)
    assert f"Max-Age={int(session.SESSION_TTL_SECONDS)}" in set_cookie

    cookie_value = fresh.cookies[session.COOKIE_NAME]
    assert session.validate_cookie(cookie_value) is not None


def test_session_cookie_persists_across_requests(client):
    """The same session id is reused on a follow-up request (no re-issue)."""
    first_session_id = session.validate_cookie(client.cookies[session.COOKIE_NAME])

    resp = client.get("/health")

    assert "set-cookie" not in resp.headers
    assert session.validate_cookie(client.cookies[session.COOKIE_NAME]) == first_session_id


def test_jobs_endpoint_without_cookie_returns_403():
    """AC2: missing session cookie -> 403 on /jobs/*."""
    fresh = TestClient(app, base_url="https://testserver")

    resp = fresh.get("/jobs/does-not-exist/status")

    assert resp.status_code == 403
    body = resp.json()
    assert body["error"] == "forbidden"
    assert "session" in body["message"]


def test_jobs_endpoint_with_tampered_cookie_returns_403():
    """AC2: a cookie whose signature doesn't verify -> 403."""
    fresh = TestClient(app, base_url="https://testserver")
    fresh.cookies.set(session.COOKIE_NAME, "not-a-real-session.deadbeef")

    resp = fresh.get("/jobs/does-not-exist/status")

    assert resp.status_code == 403
    assert resp.json()["error"] == "forbidden"


def test_jobs_endpoint_with_unknown_session_id_returns_403():
    """AC2: a validly-signed cookie for a session that was never issued -> 403."""
    fresh = TestClient(app, base_url="https://testserver")
    fresh.cookies.set(session.COOKIE_NAME, session.sign("never-issued-session-id"))

    resp = fresh.get("/jobs/does-not-exist/status")

    assert resp.status_code == 403


def test_non_jobs_endpoint_does_not_require_cookie():
    """Non-/jobs/* paths work without a session cookie (and mint one)."""
    fresh = TestClient(app, base_url="https://testserver")

    resp = fresh.get("/health")

    assert resp.status_code == 200


def test_session_id_is_cryptographically_random():
    """AC3: session ids are secrets.token_urlsafe(32)."""
    session.clear()
    created = session.create()

    assert len(created.session_id) == 43
    assert re.fullmatch(r"[A-Za-z0-9_-]+", created.session_id)

    other = session.create()
    assert other.session_id != created.session_id


def test_cookie_max_age_matches_session_ttl():
    """AC4: cookie Max-Age equals the server-side session TTL."""
    assert session.cookie_kwargs()["max_age"] == int(session.SESSION_TTL_SECONDS)


def test_expired_session_is_rejected_and_logged(client, session_id, capsys):
    """AC4: a session idle past SESSION_TTL_SECONDS is reaped and logged."""
    server_session = session._SESSIONS[session_id]
    server_session.last_accessed = datetime.now(timezone.utc) - timedelta(seconds=session.SESSION_TTL_SECONDS + 1)

    resp = client.get("/jobs/does-not-exist/status")

    assert resp.status_code == 403
    assert session_id not in session._SESSIONS

    events = _events(capsys.readouterr().out)
    expired = next(e for e in events if e["event"] == "session_expired")
    assert expired["session_id"] == session_id


def test_job_inaccessible_to_other_session(client):
    """AC5: a job is 404 (not 403) to a session that didn't create it."""
    job_id = _submit_batch(client).json()["job_id"]

    other = TestClient(app, base_url="https://testserver")
    other.get("/health")

    resp = other.get(f"/jobs/{job_id}/status")

    assert resp.status_code == 404


def test_job_accessible_to_owning_session(client):
    """Sanity check: the creating session can read its own job."""
    job_id = _submit_batch(client).json()["job_id"]

    resp = client.get(f"/jobs/{job_id}/status")

    assert resp.status_code == 200
