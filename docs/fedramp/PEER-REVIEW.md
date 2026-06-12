# Independent Peer Review — FedRAMP Documentation Package

| | |
|---|---|
| **System Name** | Alcohol Label Verification App (ALVA) — TTB COLA Automation PoC |
| **Document Status** | **FINAL** |
| **Date** | 2026-06-11 |
| **Issue** | ISSUE 4.5 — Complete FedRAMP Documentation Package (AC8) |
| **Reviewer** | Independent agent review (AC8) — no prior involvement in authoring this package |
| **Related Documents** | [`SSP-final.md`](./SSP-final.md), [`POAM.md`](./POAM.md), [`DATA-FLOW-final.md`](./DATA-FLOW-final.md), [`SAST-RESULTS.md`](./SAST-RESULTS.md), [`CONTROL-MATRIX.xlsx`](./CONTROL-MATRIX.xlsx), [`INCIDENT-RESPONSE-PLAN.md`](./INCIDENT-RESPONSE-PLAN.md), [`SYSTEM-BOUNDARY.png`](./SYSTEM-BOUNDARY.png), [`README.md`](./README.md) |

---

## 1. Review scope and methodology

This review independently verifies the FedRAMP documentation package produced under
**ISSUE 4.5** against (a) the actual application source code, (b) the predecessor
documents it supersedes (`SSP-draft.md`, `DATA-FLOW.md`, the Phase 2 baseline of
`SAST-RESULTS.md`), and (c) the FedRAMP Control Coverage Matrix in
[`../../project-management/PROJECT-PLAN.md`](../../project-management/PROJECT-PLAN.md).

The reviewer had no role in drafting any of the reviewed documents, satisfying AC8
("Peer-reviewed by at least one team member not involved in implementation").

Methodology, in order:

1. Read every document in the package end to end (`SSP-final.md`, `POAM.md`,
   `DATA-FLOW-final.md`, `SAST-RESULTS.md`, `INCIDENT-RESPONSE-PLAN.md`, `README.md`,
   `SYSTEM-BOUNDARY.png`, `assets/system-boundary.mmd`).
2. Spot-checked dozens of specific code-reference claims (file paths, function/constant
   names, environment variables, exception types, HTTP status codes) directly against
   `backend/app/`, `backend/ocr/`, `backend/batch/`, `backend/matching/`, and
   `frontend/src/`.
3. Verified `CONTROL-MATRIX.xlsx` programmatically with `openpyxl` (33 rows, status
   distribution, cross-check against `SSP-final.md` §8 and `POAM.md`).
4. Re-ran `bandit` and `pip-audit` locally and compared output against
   `SAST-RESULTS.md`'s quoted "final scan re-run" blocks.
5. Ran the relevant backend pytest modules (`test_audit_logging.py`,
   `test_session_store.py`, `test_input_validation.py --collect-only`) to confirm
   referenced test coverage exists and passes.
6. Diffed `SAST-RESULTS.md` against its prior committed version (`git show
   2c1d34a:docs/fedramp/SAST-RESULTS.md`) and `SSP-final.md`/`DATA-FLOW-final.md`
   against `SSP-draft.md`/`DATA-FLOW.md` to confirm the claimed deltas (§11 of
   `SSP-final.md`) are accurate.
7. Checked every markdown cross-reference link in the package for resolution to a real
   file (or an acknowledged forward-reference to a Pending document).

No reviewed document was modified. No git state was changed, no Docker images were
built, and no full test suite was run (per the review's read-only scope).

---

## 2. Findings

### Blocking

None.

### Major

None.

### Minor

**Finding A — `session_expired` audit event has two semantically different
`session_id` namespaces, undocumented.**

- **Checked:** `backend/app/session.py::_reap_expired` and
  `backend/batch/store.py::_reap_expired`, both of which call
  `audit.log_session_expired(session_id=...)`; `DATA-FLOW-final.md` §4.3 / event
  inventory.
- **Found:** `app/session.py::_reap_expired` emits `session_expired` with the real
  browser **authentication session id** (the value bound to the signed cookie).
  `batch/store.py::_reap_expired` emits the *same* event name, `session_expired`, but
  passes the **batch job id** as the `session_id` field
  (`log_session_expired(session_id=job_id)`). `DATA-FLOW-final.md` (line ~158) and
  `SSP-final.md` §8 (SI-12 row) describe only the job-reaper source, without noting that
  an identically-named audit event can carry an id from either of two different
  namespaces (auth session vs. batch job).
- **What should change before ATO:** Either (a) rename one of the two events (e.g.
  `job_expired` vs. `session_expired`) so they are distinguishable in log-based
  analysis, or (b) explicitly document in `DATA-FLOW-final.md` §3/§4.3 and
  `SESSION-MANAGEMENT.md` that `session_expired` is emitted from two call sites with
  different `session_id` semantics, so an ISSO doing IR-8 log triage doesn't assume a
  single namespace. This is a documentation/observability clarity issue, not a security
  control gap.

**Finding B — `RateLimitError` omitted from the OCR fail-over exception list in
`SSP-final.md` §7 and `DATA-FLOW-final.md` §3, while CP-10's own example scenario
relies on it.**

- **Checked:** `backend/ocr/adapter.py::extract_fields` exception handling (line
  ~100-106); `SSP-final.md` §7 (Claude Vision interconnection row) and §8 (CP-10 row);
  `DATA-FLOW-final.md` §3 (TB-3 fail-open behavior bullet); `INCIDENT-RESPONSE-PLAN.md`
  §3/§4.1.
- **Found:** The code catches **five** exception types for fail-over to local
  Tesseract: `anthropic.APITimeoutError`, `anthropic.APIConnectionError`,
  `anthropic.RateLimitError`, `TimeoutError`, `ConnectionError`. `SSP-final.md` §7 and
  `DATA-FLOW-final.md` §3 both enumerate only **four**, omitting `RateLimitError` — yet
  `SSP-final.md` §8's CP-10 row explicitly cites *"the cloud OCR provider ... becomes
  unavailable mid-batch (e.g., its rate limit is exceeded)"* as the worked example for
  this same fail-over path. `INCIDENT-RESPONSE-PLAN.md` §3 correctly lists all five.
- **What should change before ATO:** Add `RateLimitError` to the exception lists in
  `SSP-final.md` §7 and `DATA-FLOW-final.md` §3 so the three documents are consistent
  and the CP-10 narrative example (rate-limit triggers fail-over) is backed by the
  enumerated trigger list. Low severity — the code behavior is correct and tested; this
  is a cross-document accuracy gap only.

**Finding E — `SAST-RESULTS.md`'s "Backend — Bandit" reproduction command and LOC
figure no longer match what CI actually runs.**

- **Checked:** `.github/workflows/ci.yml` line 82 (`bandit -r backend -f sarif -o
  bandit.sarif --severity-level high --confidence-level high`); `SAST-RESULTS.md`
  "Backend — Bandit" section and "Reproducing locally" section
  (`bandit -r app ocr matching batch --severity-level high --confidence-level high`);
  `git show 2c1d34a:docs/fedramp/SAST-RESULTS.md` (Phase 2 baseline).
- **Found:** The Phase 4 update changed the documented Bandit command from the Phase
  2 baseline's `bandit -r backend -f sarif -o bandit.sarif --severity-level high
  --confidence-level high` (which matches CI exactly and scans the whole `backend/`
  tree, including `tests/` and `scripts/`, ~3,694 LOC) to the narrower `bandit -r app
  ocr matching batch --severity-level high --confidence-level high` (1,790 LOC,
  excludes `tests/` and `scripts/`). The quoted output block ("Total lines of code:
  1790 ... 0 findings") is real and reproducible for the narrower scope — independently
  reproduced both the narrower scope (1,790 LOC, 0 findings) and the full `backend/`
  scope (~3,694 LOC, 0 HIGH/HIGH findings) during this review, so the headline
  conclusion ("0 findings, unchanged from baseline") holds either way. However, as
  written the document presents the 1,790-LOC figure as *the* final scan re-run result
  without noting it is narrower than the CI invocation it claims to mirror (§intro
  "Scope note": *"re-running every scanner in `ci.yml`"*).
- **What should change before ATO:** Either restore the `bandit -r backend ...`
  invocation (matching CI and the Phase 2 baseline) for the quoted reproduction output,
  or — if the narrower `app ocr matching batch` scope is intentional (e.g., to exclude
  test/tooling code from the application-code SAST claim) — add a one-line note
  explaining the scope difference from the CI command referenced in the "Scope note" at
  the top of the document. No security risk either way; both scopes are clean.

**Finding F — Trivy `alvf-frontend` "Total: 3" does not match its 2-row CVE table.**

- **Checked:** `SAST-RESULTS.md` "Docker images — Trivy" section, `alvf-frontend`
  subsection; `git show 2c1d34a:docs/fedramp/SAST-RESULTS.md` (baseline `alvf-frontend`
  section, which had a single-row table with no "Total:" line).
- **Found:** The Phase 4 update added explicit `Total: N (HIGH: N, CRITICAL: 0)`
  summary lines per image. For `alvf-backend`, "Total: 3" correctly matches its 3-row
  table (`libssl3t64/openssl/openssl-provider-legacy`, `jaraco.context`, `wheel`). For
  `alvf-frontend`, however, the section states **"Total: 3 (HIGH: 3, CRITICAL: 0)"**
  immediately above a table that lists only **2 rows** (`libcrypto3 / libssl3`,
  `libxml2`). The narrative paragraph above the table ("one new finding since baseline
  ... `libxml2` is unchanged") is consistent with 2 findings, not 3. This looks like a
  copy/paste of the "Total: 3" line from the `alvf-backend` subsection that wasn't
  updated for the frontend's actual count of 2.
- **What should change before ATO:** Correct the `alvf-frontend` "Total:" line to
  "Total: 2 (HIGH: 2, CRITICAL: 0)" (or add a third row if a third finding was intended
  but omitted from the table). This does not change the gating conclusion (0 CRITICAL
  in both images, POAM correctly carries no Trivy item), but as written it is an
  internal arithmetic inconsistency an ISSO is likely to flag immediately.

### Nit

**ErrorBoundary fallback text quoted as a single string, but rendered as two
elements.**

- **Checked:** `frontend/src/components/ErrorBoundary.jsx`; `SSP-final.md` §8 (SI-17
  row); `INCIDENT-RESPONSE-PLAN.md`.
- **Found:** Both documents quote the fallback UI as one em-dash-joined string,
  *"Something went wrong — your session is still active"*. The component actually
  renders this as two separate elements: `<h1>Something went wrong</h1>` and
  `<p>Your session is still active. You can return to the start and try again.</p>`.
  `frontend/src/__tests__/errorBoundary.test.jsx` asserts on the heading and paragraph
  text separately, matching the real DOM structure.
- **What should change before ATO:** Optional. The combined quote captures the meaning
  correctly and the underlying control (SI-17, AC5) is implemented and tested as
  described; only the literal quoted string in the docs doesn't match the DOM verbatim.
  Cosmetic only — would not block hand-off.

### Observations

**Finding C — `OCR_MODE=auto (or cloud)` / `auto/cloud` phrasing implies a
configuration value that does not exist.**

- **Checked:** `backend/ocr/adapter.py` (lines ~28, ~94); `.env.example`;
  `SSP-final.md` §4, §6; `DATA-FLOW-final.md`.
- **Found:** `SSP-final.md` and `DATA-FLOW-final.md` repeatedly phrase the
  cloud-OCR-enabled configuration as `OCR_MODE=auto (or cloud)` / `OCR_MODE=auto/cloud`,
  as if `cloud` were a second, distinct, supported value. In the code, the only
  meaningful branch is `OCR_MODE == "local"`; any other value (including a hypothetical
  `"cloud"`) falls through to the same "try Claude Vision, fail over to Tesseract"
  branch as `"auto"`. `.env.example` documents only `auto` and `local` as valid values
  — `cloud` does not appear anywhere in code or config.
- **Assessment:** Not a functional bug — setting `OCR_MODE=cloud` would behave
  identically to `auto` (since it's `!= "local"`), so no operator misconfiguration risk
  results. However, the phrasing implies a third documented mode that doesn't exist as a
  distinct, recognized value. Consider simplifying to `OCR_MODE=auto` (or any value
  other than `local`) in both SSP-final.md and DATA-FLOW-final.md to avoid implying a
  config option that isn't real. Low priority.

**Finding D — Optional `with-redis` Docker Compose profile is not mentioned in the
authorization boundary (§4) or system interconnections (§7) of `SSP-final.md`.**

- **Checked:** `.env.example` (`REDIS_URL` documented as optional, "leave blank to use
  the in-process dict store"); `docker-compose.yml` (`with-redis` profile defines a
  digest-pinned `redis:7-alpine` service, with `REDIS_URL: ${REDIS_URL:-}` wired into
  the backend's environment); grep of `backend/app/`, `backend/ocr/`, `backend/batch/`,
  `backend/matching/` for `redis`/`REDIS_URL` (excluding `.venv`) — zero matches.
- **Found:** Redis is fully unwired in application code — `SSP-final.md` §3 ("Storage —
  none") and `DATA-FLOW-final.md` §7 ("not Redis/disk-backed") are technically correct
  that Redis is *not used*. However, neither §4 (Authorization Boundary) nor §7 (System
  Interconnections) of `SSP-final.md` acknowledges the existence of the optional
  `with-redis` Compose profile at all. An ISSO who inspects `docker-compose.yml`
  directly (a reasonable verification step) could reasonably ask whether this
  unreferenced service/profile is in scope for the authorization boundary, or whether it
  represents dead configuration that should be removed before ATO.
- **Assessment:** CM-6 configuration-hygiene observation (dead/unused optional
  scaffolding), not a control-implementation gap — the boundary diagram and SI-12/SC-28
  claims (in-memory only, no persistent store) remain accurate as long as the
  `with-redis` profile is never activated. Consider either removing the unused profile
  or adding a one-line note in §4/§7 explicitly stating it is out of scope / disabled by
  default and not part of the authorized boundary.

---

## 3. Verification checks performed

| # | Check | Result |
|---|---|---|
| 1 | `CONTROL-MATRIX.xlsx` via `openpyxl` (`backend/.venv/Scripts/python.exe`, run from `backend/`) | 33 data rows; status distribution `Counter({'Implemented': 32, 'Planned': 1})`; only `RA-3` is `Planned`; all control IDs match `SSP-final.md` §8; `Summary` sheet shows Total=33, Implemented=32, Planned=1, NA=0, Inherited=0, Remaining gap = RA-3 |
| 2 | `POAM.md` §1/§2/§3 vs. `CONTROL-MATRIX.xlsx`/`SSP-final.md` §8 | §1 has exactly 1 open item (RA-3, Risk=Low, Status=Open, remediation=ISSUE 4.6); §2 lists SI-12 and IR-8 as resolved since `SSP-draft.md`; §3 summary (33 total / 32 Implemented / 1 Planned) matches the spreadsheet |
| 3 | `README.md` status table | All artifacts **Final**/Complete except `THREAT-MODEL.md` (4.6, Pending) and `PEER-REVIEW.md` (4.5, Pending — resolved by this document) |
| 4 | `SYSTEM-BOUNDARY.png` vs. `assets/system-boundary.mmd` vs. `SSP-final.md` §4 mermaid block | All three match exactly — TB-0 (Reviewer↔Frontend, HTTPS + session cookie), TB-1 (Frontend↔Backend, internal HTTP / Docker bridge), TB-2 (Backend↔Tesseract, in-process, no network), TB-3 (Backend↔Claude Vision, HTTPS/TLS 1.2+, SC-8/SA-9), in-memory store labeled SI-12 |
| 5 | `bandit -r app ocr matching batch --severity-level high --confidence-level high` (`.venv/Scripts/python.exe -m bandit ...`) | "Total lines of code: 1790", 0 issues at any severity/confidence — exact match to `SAST-RESULTS.md` |
| 6 | `bandit -r backend --severity-level high --confidence-level high -x ./.venv` (full CI scope) | ~3,694 LOC, 0 High/High issues — conclusion ("0 findings") holds for the broader CI scope too, but LOC figure differs from the document's quoted 1,790 (see Finding E) |
| 7 | `pip-audit -r requirements.txt --strict` | "No known vulnerabilities found" — matches `SAST-RESULTS.md` |
| 8 | `pytest tests/test_audit_logging.py tests/test_session_store.py -q` | 11 passed |
| 9 | `pytest tests/test_input_validation.py -q --collect-only` | 25 tests collected — matches "20+ case fuzz suite" claim (SI-10) |
| 10 | `git diff` / `git show 2c1d34a:docs/fedramp/SAST-RESULTS.md` (baseline vs. final) | Confirmed header table added, Bandit command/LOC scope changed (Finding E), Trivy `alvf-frontend` gained `libcrypto3`/`libssl3` (CVE-2026-45447) finding with "Total: 3" inconsistency introduced (Finding F) |
| 11 | `SSP-draft.md` → `SSP-final.md`, `DATA-FLOW.md` → `DATA-FLOW-final.md` diffs | TB-1 wording correction (HTTPS reverse proxy → internal HTTP/Docker bridge), SI-12/IR-8 Planned→Implemented, `backend/app/jobstore.py` → `backend/batch/store.py` path correction — all confirmed accurate against current source tree |
| 12 | Code spot-checks: `backend/app/pipeline.py`, `audit.py`, `main.py`, `batch/store.py`, `app/session.py`, `routers/verify.py`, `app/validation.py`, `app/models.py`, `routers/jobs.py`, `matching/exact_validator.py`, `ocr/preprocessor.py`, `batch/orchestrator.py`, `ocr/adapter.py`, `requirements.txt`, `.env.example`, `docker-compose.yml` | All quoted constants, function names, env vars, status codes, and behaviors verified accurate except the items noted in Findings A, B, C, D |
| 13 | Frontend spot-checks: `ErrorBoundary.jsx`, `useJobStream.js`, `BatchPage.jsx`, `errorBoundary.test.jsx`, `eslint.config.js` | All confirmed accurate except the ErrorBoundary text-combination Nit |
| 14 | `docker/nginx/default.conf`, `docker/backend.Dockerfile` | TB-1 internal HTTP (`proxy_pass http://backend:8000/`, `proxy_buffering off` for SSE) and digest-pinned base image + unprivileged `app` user (CM-7) confirmed |
| 15 | Cross-reference link resolution (`SESSION-MANAGEMENT.md`, `LOAD-TEST-RESULTS.md`, `ACCESSIBILITY-REPORT.md`, `PREPROCESSING-AB-TEST.md`, `ADR-001-System-Architecture.md`, `SSP-draft.md`, `DATA-FLOW.md`, `THREAT-MODEL.md`) | All resolve to real files except `THREAT-MODEL.md`, which is consistently and correctly referenced as Pending (ISSUE 4.6) everywhere it is linked |
| 16 | `project-management/PROJECT-PLAN.md` FedRAMP Control Coverage Matrix | Exactly 29 control IDs + 4 PoC-specific additions (AU-14, SI-11, CP-10, PL-8) = 33, matching `CONTROL-MATRIX.xlsx` |
| 17 | `.github/workflows/ci.yml` | `security-events: write` permission and SARIF upload (`github/codeql-action/upload-sarif@v3`) for both Bandit and Trivy confirmed |

---

## 4. Overall verdict

**Approved with minor notes.**

The package is fundamentally sound. Every major claim — the 33-control matrix and its
32-Implemented/1-Planned (RA-3) split, the POA&M's single open item, the
authorization-boundary diagram and its three trust boundaries, the session-cookie
implementation, the OCR fail-over architecture, the in-memory/no-persistence posture,
the per-label error isolation, and the SAST/SCA/container-scan "0 CRITICAL, 0
HIGH/HIGH-application-code" headline conclusions — was independently verified against
the actual codebase and holds up. Internal consistency across `SSP-final.md`,
`POAM.md`, `CONTROL-MATRIX.xlsx`, and `README.md` is intact, and `SYSTEM-BOUNDARY.png`
is an exact rendering of its mermaid source and the SSP §4 narrative.

Six minor/nit/observation-level issues were found (Findings A, B, C, D, E, F, plus the
ErrorBoundary text Nit). None represent unmitigated technical risk, a missing control
implementation, or a new gap beyond the already-tracked RA-3 item. All are
documentation-accuracy or cross-document-consistency issues that should be cleaned up
before formal ATO submission — **Finding F** (the Trivy `alvf-frontend` "Total: 3" vs.
2-row table mismatch) is the one most likely to draw an immediate ISSO question, since
it's a simple arithmetic inconsistency in a security-scan results table.

---

## 5. Closing note

This review satisfies **AC8** of **ISSUE 4.5** ("Peer-reviewed by at least one team
member not involved in implementation") via independent-agent review. It is not a
substitute for formal human peer review by a TTB-designated reviewer, but it provides an
evidence-based, code-verified second pass over the package prior to hand-off.

None of the findings above represent a *new* control gap distinct from the already-open
**RA-3** item tracked in [`POAM.md`](./POAM.md); accordingly, no new POA&M entry is
proposed. Findings A, B, C, D, E, and F are documentation-accuracy and
cross-document-consistency corrections that the documentation owner should apply to
`SSP-final.md`, `DATA-FLOW-final.md`, and `SAST-RESULTS.md` directly (this reviewer has
made no edits to any reviewed document, per the review's scope).
