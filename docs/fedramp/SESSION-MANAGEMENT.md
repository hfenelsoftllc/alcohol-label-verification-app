# Session Management — Browser Authentication

**FedRAMP Controls:** AC-3 (Access Enforcement), IA-2 (Identification and Authentication),
SC-23 (Session Authenticity)
**Issue:** 3.7 — Implement Session Authentication

## Overview

The PoC has no user accounts — reviewers are anonymous. Instead, each browser
is identified by an opaque, server-issued **session id**, used to (a) prove
the request came from a browser the server has seen before (IA-2), and (b)
scope batch jobs so one browser cannot read another's results (AC-3).

This is a single, additional concept layered on top of two pre-existing
"session"-shaped things in this codebase, which it does not change:

| Name | Where | Purpose |
|---|---|---|
| `VerificationResult.session_id` | `app/stubs.new_session_id()` | Per-verification correlation id, used in frontend routes (`/results/:sessionId`) and export filenames. Unrelated to browser identity. |
| Job TTL ("session" in `batch/store.py`) | `batch/store.SESSION_TTL_HOURS` | How long a batch job's results are retained in memory before being reaped (ISSUE 3.5/SI-12). |
| **Browser auth session (this doc)** | `app/session.py` | Identifies the browser. Carried in the `session_id` cookie; checked by middleware on every request. |

## Lifecycle

1. **Issuance (AC1).** On the first request to any non-`/jobs/*` path, the
   `session_authentication` middleware (`app/main.py`) finds no valid session
   cookie, mints a new session via `session.create()` — id =
   `secrets.token_urlsafe(32)` (AC3) — and sets it as a signed cookie on the
   response.
2. **Validation.** On every subsequent request, the middleware reads the
   `session_id` cookie, verifies its HMAC-SHA256 signature
   (`session._unsign`, stdlib `hmac.compare_digest`), and looks up the
   session id in the in-memory store. A request whose cookie is missing,
   tampered, or for a session that was never issued or has expired is treated
   identically: no valid session.
3. **Refresh.** A successful validation updates `last_accessed`, extending
   the session's idle TTL — consistent with the job-store refresh pattern in
   `batch/store.get_job`.
4. **Expiry (AC4, SI-12).** A session idle longer than `SESSION_TTL_HOURS`
   (default 4, shared with the job store's TTL) is reaped — either lazily on
   the next `validate_cookie` call for that session, or via the same
   `_reap_expired` sweep that runs each time `session.create()` mints a new
   session. Reaping logs a `session_expired` event (`app/audit.py`), the same
   event already emitted by `batch/store.py` for expired jobs.

## Access enforcement (AC2/AC3)

The `session_authentication` middleware gates every `/jobs/*` request:

- **No valid session** → `403 Forbidden`, `{"error": "forbidden", "message":
  "missing or invalid session", ...}`, logged via `log_error`. This covers a
  missing cookie, a tampered/forged signature, and a signature that verifies
  but whose session was never issued or has been reaped.
- **Valid session** → the request proceeds with `request.state.auth_session_id`
  set, consumed via the `session.get_session_id` FastAPI dependency.

All other paths (`/health`, `/verify`, `/verify/batch`, `/docs`, ...) work
without a session cookie and transparently mint one if absent, so a cookie
exists before the browser's first batch submission.

## Per-session job isolation (AC5)

`POST /verify/batch` stamps the new `Job` with the caller's
`auth_session_id` (`batch/store.Job.session_id`). Every `/jobs/{job_id}/...`
route resolves the job via `_require_job(job_id, session_id)`
(`app/routers/jobs.py`), which returns `404 Not Found` — the same response as
a job that doesn't exist — if the job belongs to a different session. This
deliberately uses 404 rather than 403: a session with no/invalid cookie gets
403 (it can't reach this code at all), while a session with a *valid* cookie
but the wrong job gets the same "not found" response a guess at a random
`job_id` would get, so it can't be used to enumerate or confirm other
sessions' job ids.

There is no admin or cross-session view — each session can only ever see jobs
it created itself.

## Cookie attributes (AC1, AC4, SC-23)

Set via `session.cookie_kwargs()`:

| Attribute | Value | Why |
|---|---|---|
| `HttpOnly` | `true` | Not readable from JavaScript — mitigates session-id theft via XSS. |
| `Secure` | `true` | Only sent over HTTPS. |
| `SameSite` | `strict` | Never sent on cross-site requests — mitigates CSRF. |
| `Max-Age` | `SESSION_TTL_HOURS * 3600` | Matches the server-side session TTL (AC4) — the cookie does not outlive the session it names. |
| `Path` | `/` | Sent on every backend route, including `/jobs/*`. |

The cookie value is `"{session_id}.{hmac_sha256_hex}"`. The HMAC lets the
server reject a forged or tampered session id without a store lookup; the
subsequent store lookup rejects a syntactically-valid signature for a session
that was never issued or has since been reaped.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SESSION_TTL_HOURS` | `4` | Idle timeout for both auth sessions and batch jobs (shared, ISSUE 3.5). Also sets the cookie `Max-Age`. |
| `SESSION_SECRET_KEY` | random per process | HMAC key for signing session-id cookies. Optional for a single instance (everything is in-memory and clears on restart); set explicitly (`openssl rand -hex 32`) if running multiple backend instances behind a load balancer, so cookies validate across all of them. |

## Implementation references

- `backend/app/session.py` — session store, signing, cookie helpers.
- `backend/app/main.py` — `session_authentication` middleware.
- `backend/batch/store.py` — `Job.session_id`.
- `backend/app/routers/verify.py`, `backend/app/routers/jobs.py` — job
  creation and ownership enforcement.
- `backend/tests/test_session_auth.py` — tests for AC1-AC5.

## Frontend impact

None. The frontend's `fetch`/`EventSource`/`<a download>` calls are
same-origin and send/receive cookies by default — no client-side changes were
needed.
