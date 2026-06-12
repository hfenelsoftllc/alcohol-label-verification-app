# Incident Response Plan — Alcohol Label Verification PoC

| | |
|---|---|
| **System Name** | Alcohol Label Verification App (ALVA) — TTB COLA Automation PoC |
| **Document Status** | **FINAL** — Phase 4 (ISSUE 4.5, complete FedRAMP documentation package) |
| **Version** | 1.0 |
| **Date** | 2026-06-11 |
| **Issue** | [ISSUE 4.5 — Complete FedRAMP Documentation Package](../../project-management/PROJECT-PLAN.md) |
| **FedRAMP Control** | **IR-8** (Incident Response Plan), aligned with **SI-17** (Fail-Safe Procedures, ISSUE 4.4) |
| **Related Documents** | [`SSP-final.md`](./SSP-final.md) §8/§10, [`POAM.md`](./POAM.md), [`DATA-FLOW-final.md`](./DATA-FLOW-final.md), [`SESSION-MANAGEMENT.md`](./SESSION-MANAGEMENT.md) |

> **Scope note.** This plan covers the three incident categories called out for ALVA: **OCR /
> processing failures**, **data exposure events**, and **availability incidents**. It builds
> directly on mechanisms already implemented in the codebase — the `request_id` correlation
> introduced for every request (AU-3, `backend/app/audit.py`), the `UNREADABLE_IMAGE` /
> `PROCESSING_ERROR` / `INVALID_IMAGE` error taxonomy in `backend/app/pipeline.py` (ISSUE 4.4),
> and the fail-safe behaviors documented as SI-17 in [`SSP-final.md`](./SSP-final.md) §8. This
> document does not introduce new code; it documents how an operator/ISSO uses the existing
> audit trail and error envelopes to detect, triage, and respond to incidents.

---

## 1. Purpose and Scope

This plan defines how operations staff and the development team detect, triage, contain, and
recover from incidents affecting ALVA, and how those incidents are documented for FedRAMP
continuous monitoring (CA-7). It applies to the containerized PoC deployment described in
[`SSP-final.md`](./SSP-final.md) §3–§4: a single-node Docker host running the `alvf-frontend`
and `alvf-backend` containers, with no database and no persistent storage (SC-28).

Because the system holds **no data at rest**, the blast radius of any incident is bounded by
design: the worst case for any single incident is the loss or exposure of data belonging to
**in-flight requests and unexpired batch sessions** (≤ `SESSION_TTL_HOURS`, default 4 hours,
SI-12). This plan is scoped accordingly — it favors **fast containment via restart/redeploy**
over complex recovery procedures, since there is no persistent state to restore.

---

## 2. Roles and Responsibilities

Per [`SSP-final.md`](./SSP-final.md) §10:

| Role | Incident Response Responsibility |
|---|---|
| Development Team (hfenelsoftllc and contributors) | First responder for all categories below: triages audit logs, identifies root cause, ships a fix via the standard PR/CI process (`.github/workflows/ci.yml`). |
| Information System Security Officer (ISSO) — *TBD at hand-off* | Receives incident notifications for **Moderate** and **High** severity events (§5); confirms whether agency breach-notification procedures (data exposure) or continuous-monitoring reporting (CA-7) are triggered. |
| Authorizing Official (AO) — *TBD at hand-off* | Notified for **High** severity confirmed-PII-exposure or sustained full-outage incidents; decides whether the ATO/operating posture needs to change. |

Until the ISSO/AO roles are assigned, the development team is the sole point of contact for any
incident; this is recorded as a hand-off item, not a blocker (see [`SSP-final.md`](./SSP-final.md)
§11).

---

## 3. Detection and Correlation

Every incident category below is detected through the **same audit trail** — there is no
separate monitoring stack to stand up. `backend/app/audit.py` (ISSUE 2.7) emits one
structured JSON line per event to stdout, and `backend/app/main.py`'s `add_request_id`
middleware stamps every request with a `request_id` (returned to the client in the
`X-Request-ID` header and in every `ErrorResponse`), so a single failed reviewer action can be
traced end-to-end through the log stream.

| Audit Event | Emitted From | What It Signals |
|---|---|---|
| `request_error` (`error=http_error\|validation_error\|internal_error`) | `backend/app/main.py` exception handlers | A request failed at the HTTP layer; `error` and `message` (plain language, no stack trace per SI-11) classify the failure; the real exception is captured server-side via `logger.exception` for the catch-all handler only (IR-8 detection input, never shown to the client). |
| `match_completed` with `overall_status="ERROR"` | `backend/app/pipeline.py::run_verification` via the calling router | A label could not be processed — correlates to `UNREADABLE_IMAGE`, `PROCESSING_ERROR`, or `INVALID_IMAGE` in `VerificationResult.government_warning.issues` and the plain-language `message` field. |
| `ocr_completed` with `ocr_engine_used="tesseract"` while `OCR_MODE` is not `local` (e.g. `auto`) | `backend/ocr/adapter.py::extract_fields` | The cloud OCR call (Claude Vision) failed over to local Tesseract for this label (`APITimeoutError`/`APIConnectionError`/`RateLimitError`/`TimeoutError`/`ConnectionError`). A handful is normal; a sustained 100% fallback rate indicates a Claude Vision **availability incident** (§4.3). |
| `session_expired` | `backend/batch/store.py::_reap_expired` (SI-12) | A batch job was reaped after `SESSION_TTL_HOURS` of inactivity. Normal background behavior; a sudden spike across many sessions at once may indicate reviewers were unable to complete their batches (possible availability incident). |
| `request_completed` (`status_code >= 500`) | `backend/app/main.py` request-timing middleware | A 5xx was returned for a request; aggregate count over time is the primary availability signal. |

**Triage starting point:** grep the stdout log stream for the `request_id` reported in the
reviewer's error message (or, for a class of failures, for the relevant event name/`error`
value above) to reconstruct the full `request_received` → … → `request_completed`/`request_error`
sequence for that request.

---

## 4. Incident Categories and Response Procedures

### 4.1 OCR / Processing Failures

**Symptoms** (per `backend/app/pipeline.py`, ISSUE 4.4):

| Condition | `overall_status` | `message` shown to reviewer | Audit signal |
|---|---|---|---|
| `assess_image_quality` returns `issues == ["unreadable"]` | `ERROR` | *"Image quality too low to extract any fields"* (`UNREADABLE_IMAGE_MESSAGE`) | `match_completed` (`overall_status="ERROR"`), `government_warning.issues=["UNREADABLE_IMAGE"]` |
| Any unexpected exception during OCR, matching, or warning validation | `ERROR` | *"This label could not be processed due to an unexpected error. Please try again."* (`PROCESSING_ERROR_MESSAGE`) | `match_completed` (`overall_status="ERROR"`), `government_warning.issues=["PROCESSING_ERROR"]`, plus a server-side `logger.exception` traceback |
| Image bytes fail basic format validation before the pipeline | HTTP 415/422 `ErrorResponse{error: "http_error"\|"validation_error"}` | *"This file could not be read as an image. Please check the file and try again."* (`INVALID_IMAGE_MESSAGE`) or validation message | `request_error` |
| Any other unhandled exception reaching FastAPI | HTTP 500 `ErrorResponse{error: "internal_error", message, request_id}` | Generic plain-language message (never a stack trace, SI-11/SI-17) | `request_error` (`error="internal_error"`) |

**Response procedure:**

1. **Single-label, isolated** (`UNREADABLE_IMAGE` / `INVALID_IMAGE` for one upload): no incident.
   This is expected reviewer-facing behavior — the reviewer is instructed to re-upload a clearer
   image. No escalation.
2. **Batch, partial failure**: `backend/batch/orchestrator.py` isolates each label's failure to
   its own result (AC4) — confirm the batch summary shows the remaining labels completed
   normally (`overall_status` other than `ERROR`). No incident if failures are limited to a few
   genuinely poor-quality images.
3. **`PROCESSING_ERROR` or `internal_error` recurring across multiple, otherwise-valid images**:
   treat as a **Moderate**-severity incident (§5).
   - Pull the server-side traceback for the affected `request_id`(s) from the `logger.exception`
     output (catch-all handler, `backend/app/main.py`).
   - Determine whether the failure is in OCR (`backend/ocr/`), matching
     (`backend/matching/`), or preprocessing (`backend/ocr/preprocessor.py` — note
     preprocessing is designed to degrade back to original bytes on failure and should not
     itself cause `PROCESSING_ERROR`; if it does, that is the defect).
   - File a defect, fix, and add a regression test before closing the incident.
4. **`internal_error` rate spikes across unrelated endpoints** (not just `/verify*`): treat as
   an **availability incident** (§4.3) — this usually indicates an infrastructure-level problem
   (e.g., the backend container is in a bad state), not a per-label data issue.

### 4.2 Data Exposure Events

**What would constitute exposure**, given the PII inventory in
[`SSP-final.md`](./SSP-final.md) §6 (the `name_address` field, and label images that may show a
Name & Address):

- `name_address` (or raw label-image bytes / base64) appears in stdout logs, an error
  `message`, or a stack trace.
- Label image bytes are transmitted to any external endpoint **other than** the single
  whitelisted Claude Vision endpoint (`api.anthropic.com`), or are transmitted even when
  `OCR_MODE=local`.
- A reviewer's session can access another session's batch job results (an AC-3 session-scoping
  failure — see [`SESSION-MANAGEMENT.md`](./SESSION-MANAGEMENT.md)).

**Detection:**

- **Automated (continuous, CA-7):** `backend/tests/test_audit_logging.py::test_logs_never_contain_pii`
  runs on every PR (`.github/workflows/ci.yml`) and asserts the literal `name_address` string and
  base64 image payloads never appear in captured log output. A CI failure on this test is itself
  a **High**-severity finding and must not be merged.
- **Manual (operator/ISSO log review):** periodically grep the stdout log stream for the
  `name_address` field name and for long base64-looking strings; none should ever appear,
  because every `backend/app/audit.py` helper has an explicit keyword-only signature that
  structurally excludes them (§AU-9 in [`SSP-final.md`](./SSP-final.md) §8).
- **Network egress (inherited control):** the hosting GSS's network monitoring should confirm
  the backend container's only outbound destination (when `OCR_MODE` is not `local`, e.g.
  `auto`) is `api.anthropic.com` over TLS. Any other outbound destination is an exposure
  incident.
- **Session isolation:** `backend/app/routers` (per AC-3, ISSUE 3.7) returns 404 for any
  `/jobs/{id}` request whose session does not own that job. A confirmed cross-session read is a
  **High**-severity finding.

**Response procedure:**

1. **Confirmed PII in logs**: treat as **High** severity (§5).
   - **Contain immediately**: this is a code defect, not a configuration issue — there is no
     "turn off logging" switch needed because `LOG_LEVEL` does not control *what* is logged,
     only verbosity. Identify and patch the call site that passed the sensitive value into an
     `audit.log_*` helper or a generic `logger.info`/`logger.exception` call.
   - **Eradicate**: add the offending value/pattern to
     `backend/tests/test_audit_logging.py::test_logs_never_contain_pii` as a regression case
     before closing.
   - **Notify**: escalate to the ISSO (§2) for an agency breach-notification determination —
     this is a policy decision outside the codebase.
2. **Unexpected external transmission** (egress to a non-whitelisted host, or any egress while
   `OCR_MODE=local`): treat as **High** severity.
   - **Contain immediately**: set `OCR_MODE=local` (env var, no code change, no rebuild) to stop
     all external calls — Tesseract continues to serve all OCR locally (air-gapped mode, §7 of
     [`SSP-final.md`](./SSP-final.md)). This is the fastest available containment step.
   - Investigate `backend/ocr/adapter.py` and the `anthropic` SDK configuration for the cause
     before re-enabling `OCR_MODE` to a value other than `local` (e.g. `auto`).
3. **Cross-session data access** (AC-3 failure): treat as **High** severity.
   - **Contain immediately**: rotate `SESSION_SECRET_KEY` (env var) and redeploy — this
     invalidates every existing session cookie (`SC-23`), forcing all reviewers to be
     re-identified with a fresh `secrets.token_urlsafe(32)` session id. Any in-progress batch
     jobs are lost (acceptable, §1 — no PII persists beyond `SESSION_TTL_HOURS` regardless).
   - Fix and add a regression test to the session-scoping suite before re-enabling normal
     operation.

### 4.3 Availability Incidents

**Symptoms and response:**

| Symptom | Likely Cause | Response |
|---|---|---|
| `/health` endpoint stops responding | Backend container crashed or is unresponsive | Restart the `alvf-backend` container. The system is fully stateless except for the in-memory job store (SC-28); any in-progress batch jobs are lost, and affected reviewers must resubmit. This is an accepted recovery path for a **Moderate**-availability system (FIPS 199, §2 of [`SSP-final.md`](./SSP-final.md)) and is consistent with CP-10. |
| Frontend shows **"Reconnecting…"** during a batch (`frontend/src/hooks/useJobStream.js` `reconnecting` state, rendered by `BatchPage.jsx`) | A transient SSE connection drop between the browser and the backend | No action required — the native `EventSource` reconnects automatically (AC6, ISSUE 4.4) and the backend replays any results the client missed. Escalate only if "Reconnecting…" persists for several minutes without recovering, which would indicate the backend itself is down (see row above). |
| `ocr_completed` shows `ocr_engine_used="tesseract"` for **all** labels while `OCR_MODE` is not `local` (e.g. `auto`) | Claude Vision API outage, rate-limiting, or network egress failure | No reviewer-facing action needed — `backend/ocr/adapter.py::extract_fields` has already failed over to local Tesseract automatically (CP-10, confirmed under load in [`LOAD-TEST-RESULTS.md`](../LOAD-TEST-RESULTS.md)). Confirm Anthropic's status page / agency network egress separately; once resolved, fallback reverts automatically on the next call. |
| Frontend shows the global error boundary: heading **"Something went wrong"** with the message **"Your session is still active. You can return to the start and try again."** (`frontend/src/components/ErrorBoundary.jsx`) | An unhandled JavaScript render error | Reviewer clicks "Return to start" to recover (AC5, ISSUE 4.4) without losing their session cookie/identity. Collect the browser console error (no server-side audit event is emitted for client-only render errors) and file a frontend defect. |
| Memory usage on the backend host grows steadily | `SESSION_TTL_HOURS` reaping (`backend/batch/store.py::_reap_expired`, SI-12) is not keeping pace with job creation | Confirm `session_expired` events are being emitted at a reasonable rate; if not, restart the backend container (safe, per row 1) while investigating the reaper. Reduce `SESSION_TTL_HOURS` as a temporary mitigation if batch volume is unusually high. |

**Recovery validation** (after any restart/redeploy):

1. `GET /health` returns `200`.
2. Submit a single test `/verify` request and confirm a `request_completed` audit event with
   `status_code=200`.
3. For batch-affecting incidents, confirm a new `/verify/batch` submission produces
   `job_created` → SSE progress → `done` as expected.

---

## 5. Incident Severity Levels

| Severity | Definition | Examples (from §4) | Initial Response |
|---|---|---|---|
| **High** | Confirmed or suspected PII exposure, external transmission outside the whitelisted Claude Vision endpoint, cross-session data access, or the backend fully unreachable. | `test_logs_never_contain_pii` failure; egress to a non-Anthropic host; AC-3 cross-session read; `/health` down. | Immediate containment (§4.2/§4.3); notify ISSO (§2). |
| **Moderate** | Sustained processing failures across multiple valid labels, or a Claude Vision outage with fallback active. | Recurring `PROCESSING_ERROR`/`internal_error` not explained by image quality; 100% `ocr_engine_used="tesseract"` while `OCR_MODE=auto`. | Triage and fix within normal development cadence; track in a GitHub issue. |
| **Low** | Isolated, expected per-label failures or normal TTL-driven background activity. | A single `UNREADABLE_IMAGE`/`INVALID_IMAGE` result; routine `session_expired` events. | No action — this is expected system behavior. |

---

## 6. Response Workflow

1. **Detect** — via the audit-log signals in §3, a CI failure (§4.2), or a reviewer report.
2. **Triage** — correlate by `request_id`/`session_id`, classify against §4's categories, and
   assign a severity (§5).
3. **Contain** — for High-severity items, apply the immediate containment step in §4.2/§4.3
   (e.g., `OCR_MODE=local`, rotate `SESSION_SECRET_KEY`, restart the affected container) before
   root-causing.
4. **Eradicate / Recover** — fix the underlying defect via the standard PR/CI process
   (`.github/workflows/ci.yml`, required `CI Success` check), add a regression test, and run
   recovery validation (§4.3).
5. **Post-Incident Review** — for Moderate and High severity incidents, record what happened,
   the audit-log evidence that detected it, and the fix in the closing PR description or a
   linked GitHub issue, so [`POAM.md`](./POAM.md) can be updated if the incident reveals a new
   control gap.

---

## 7. Communication Plan

- **Internal (development team):** incidents are tracked as GitHub issues in this repository,
  referencing the relevant `request_id`(s) and audit-log excerpts.
- **ISSO / AO (once assigned, §2):** Moderate and High severity incidents are summarized for the
  ISSO; High-severity confirmed PII exposure is escalated to both the ISSO and AO for an
  agency breach-notification determination. Until these roles are assigned at hand-off, the
  development team retains this responsibility.
- **Reviewers (end users):** are never shown stack traces or technical detail (SI-11/SI-17) —
  only the plain-language messages defined in `backend/app/pipeline.py` and
  `backend/app/main.py`'s `ErrorResponse`, plus the frontend's "Reconnecting…" and "Something
  went wrong" / "Your session is still active. You can return to the start and try again."
  states.

---

## 8. References

- [`SSP-final.md`](./SSP-final.md) §6 (PII Handling), §8 (SI-11/SI-12/SI-17/AC-3), §10 (Roles)
- [`POAM.md`](./POAM.md) — control gap tracking (CA-5)
- [`DATA-FLOW-final.md`](./DATA-FLOW-final.md) — trust boundaries and endpoint inventory
- [`SESSION-MANAGEMENT.md`](./SESSION-MANAGEMENT.md) — session/cookie design (IA-2, AC-3, SC-23)
- `backend/app/audit.py` — audit event helper functions (AU-2/AU-3/AU-9)
- `backend/app/main.py` — global exception handlers and `ErrorResponse` envelope (SI-11)
- `backend/app/pipeline.py` — `UNREADABLE_IMAGE`/`PROCESSING_ERROR`/`INVALID_IMAGE` taxonomy (SI-17)
- `backend/batch/store.py` — session TTL reaping and `session_expired` event (SI-12)
- `backend/ocr/adapter.py` — Claude Vision → Tesseract fail-over (CP-10)
- `frontend/src/components/ErrorBoundary.jsx`, `frontend/src/hooks/useJobStream.js` — frontend
  fail-safe UI states (SI-17 AC5/AC6)
- [`LOAD-TEST-RESULTS.md`](../LOAD-TEST-RESULTS.md) — fail-over behavior confirmed under load

---

## 9. Status

This is a **new** document delivered under **ISSUE 4.5 — Complete FedRAMP Documentation
Package** (Phase 4), satisfying AC6. It updates **IR-8** in [`SSP-final.md`](./SSP-final.md) §8
from "Planned" to **Implemented**, and is recorded in [`POAM.md`](./POAM.md) §2 as a gap closed
by this issue. No further action is required for IR-8; this plan should be revisited if
[`THREAT-MODEL.md`](./THREAT-MODEL.md) (ISSUE 4.6, RA-3) identifies additional incident
categories.
