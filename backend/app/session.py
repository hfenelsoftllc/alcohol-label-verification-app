"""Browser session authentication (ISSUE 3.7).

FedRAMP IA-2 (Identification and Authentication), SC-23 (Session
Authenticity), AC-3 (Access Enforcement): each browser is identified by a
cryptographically random session id (`secrets.token_urlsafe(32)`), carried
in an HMAC-signed, HttpOnly/Secure/SameSite=Strict cookie (`app.main`'s
session middleware). The signature lets the server reject a tampered or
forged cookie without a store lookup; the id is then checked against
`_SESSIONS` so a reaped (or never-issued) session is rejected even if the
signature still verifies.

This is distinct from `VerificationResult.session_id` (a per-verification
correlation id, ISSUE 1.4) and from the per-job TTL in `batch/store.py` —
both predate this module and are unrelated to browser identity.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status

from app import redis_client
from app.audit import log_session_expired

#: Name of the cookie carrying the signed session id (AC1).
COOKIE_NAME = "session_id"

#: How long an idle session is honored before being reaped. Configurable via
#: SESSION_TTL_HOURS (default 4 — see .env.example), the same setting used
#: by batch/store.py for job TTL (AC4: "cookie max-age matches").
SESSION_TTL_SECONDS: float = float(os.getenv("SESSION_TTL_HOURS", "4")) * 3600

#: HMAC key used to sign session-id cookies. Configurable via
#: SESSION_SECRET_KEY for deployments that need cookies to remain valid
#: across restarts/instances; otherwise a random key is generated once per
#: process, consistent with the in-memory, restart-clears-everything model.
_SECRET_KEY: bytes = (os.getenv("SESSION_SECRET_KEY") or secrets.token_hex(32)).encode()


@dataclass
class Session:
    session_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_SESSIONS: dict[str, Session] = {}


def _sign(session_id: str) -> str:
    digest = hmac.new(_SECRET_KEY, session_id.encode(), hashlib.sha256).hexdigest()
    return f"{session_id}.{digest}"


def _unsign(token: str) -> str | None:
    session_id, sep, digest = token.rpartition(".")
    if not sep:
        return None
    expected = hmac.new(_SECRET_KEY, session_id.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, expected):
        return None
    return session_id


def _is_expired(session: Session, now: datetime) -> bool:
    return (now - session.last_accessed).total_seconds() > SESSION_TTL_SECONDS


def _reap_expired() -> None:
    """Drop sessions idle longer than SESSION_TTL_SECONDS, logging each."""
    now = datetime.now(timezone.utc)
    expired = [session_id for session_id, session in _SESSIONS.items() if _is_expired(session, now)]
    for session_id in expired:
        del _SESSIONS[session_id]
        log_session_expired(session_id=session_id)


def create() -> Session:
    """Mint and store a new session with a cryptographically random id (AC3)."""
    session = Session(session_id=secrets.token_urlsafe(32))
    if redis_client.client is not None:
        redis_client.client.setex(
            f"session:{session.session_id}",
            int(SESSION_TTL_SECONDS),
            json.dumps({"created_at": session.created_at.isoformat(), "last_accessed": session.last_accessed.isoformat()}),
        )
        return session
    _reap_expired()
    _SESSIONS[session.session_id] = session
    return session


def validate_cookie(token: str | None) -> str | None:
    """Return the session id for a valid, live cookie, or None.

    Covers all three "invalid" cases (AC2): missing cookie, a signature
    that doesn't verify (tampered/forged), and a signature that verifies
    but whose session has been reaped or was never issued.
    """
    if not token:
        return None
    session_id = _unsign(token)
    if session_id is None:
        return None

    if redis_client.client is not None:
        key = f"session:{session_id}"
        if redis_client.client.get(key) is None:
            return None
        redis_client.client.expire(key, int(SESSION_TTL_SECONDS))
        return session_id

    session = _SESSIONS.get(session_id)
    if session is None:
        return None
    if _is_expired(session, datetime.now(timezone.utc)):
        del _SESSIONS[session_id]
        log_session_expired(session_id=session_id)
        return None
    session.last_accessed = datetime.now(timezone.utc)
    return session_id


def sign(session_id: str) -> str:
    """Sign `session_id` for use as a cookie value."""
    return _sign(session_id)


def cookie_kwargs() -> dict:
    """Shared Set-Cookie attributes for the session cookie (AC1/AC4)."""
    return {
        "httponly": True,
        "secure": True,
        "samesite": "strict",
        "max_age": int(SESSION_TTL_SECONDS),
        "path": "/",
    }


def get_session_id(request: Request) -> str:
    """FastAPI dependency: the caller's validated session id.

    The session middleware (`app.main`) has already rejected requests to
    `/jobs/*` with no valid session (403), so by the time a route runs this
    is always set; the exception here is defensive.
    """
    session_id = getattr(request.state, "auth_session_id", None)
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing or invalid session")
    return session_id


def clear() -> None:
    """Test helper — drop all sessions."""
    if redis_client.client is not None:
        redis_client.delete_by_prefix("session:")
        return
    _SESSIONS.clear()
