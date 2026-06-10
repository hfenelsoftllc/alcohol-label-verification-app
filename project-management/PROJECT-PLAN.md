# Alcohol Label Verification PoC — Project Management Plan

**Program:** TTB COLA Automation PoC  
**Classification:** MODERATE (FedRAMP Baseline)  
**Sprint Length:** 1 week  
**Total Duration:** 4 Sprints (4 weeks)  
**Tracking:** GitHub Projects — Kanban + Roadmap view  
**Last Updated:** 2026-06-09

---

## GitHub Project Setup

### Labels to Create

| Label | Color | Purpose |
|-------|-------|---------|
| `epic` | `#7B2D8B` | Parent epic grouping |
| `phase-1` | `#0075CA` | Foundation & Infrastructure |
| `phase-2` | `#00B4D8` | Core AI Intelligence |
| `phase-3` | `#0077B6` | Batch Processing & UI |
| `phase-4` | `#023E8A` | Hardening & ATO Prep |
| `fedramp` | `#B00020` | FedRAMP compliance work |
| `fedramp-ac` | `#D62839` | Access Control (AC) |
| `fedramp-au` | `#D62839` | Audit & Accountability (AU) |
| `fedramp-cm` | `#D62839` | Configuration Management (CM) |
| `fedramp-ia` | `#D62839` | Identification & Authentication (IA) |
| `fedramp-sc` | `#D62839` | System & Comms Protection (SC) |
| `fedramp-si` | `#D62839` | System & Information Integrity (SI) |
| `fedramp-ra` | `#D62839` | Risk Assessment (RA) |
| `fedramp-sa` | `#D62839` | System & Services Acquisition (SA) |
| `backend` | `#E36209` | Backend / API work |
| `frontend` | `#0E8A16` | UI / React work |
| `devops` | `#6F42C1` | Infrastructure / Docker / CI |
| `ai-ml` | `#F9C513` | OCR / ML / Vision work |
| `security` | `#B60205` | Security controls (non-FedRAMP) |
| `testing` | `#FBCA04` | Testing & QA |
| `documentation` | `#0075CA` | Docs, ADRs, runbooks |
| `accessibility` | `#5319E7` | WCAG / a11y work |
| `priority-critical` | `#B60205` | Must-have, blocks release |
| `priority-high` | `#E4E669` | High value / high risk |
| `priority-medium` | `#0E8A16` | Standard backlog |
| `priority-low` | `#C2E0C6` | Nice-to-have |
| `blocked` | `#E11D48` | Waiting on dependency |
| `needs-review` | `#6366F1` | PR or design needs review |

### Milestones (map to Phases)

| Milestone | Due Date | Description |
|-----------|----------|-------------|
| `Phase 1 — Foundation` | Week 1 | Monorepo, Docker, API skeleton, security baseline |
| `Phase 2 — Core Intelligence` | Week 2 | OCR, matching engine, field extraction |
| `Phase 3 — Batch & UI` | Week 3 | Bulk processing, review interface, export |
| `Phase 4 — Hardening & ATO Prep` | Week 4 | Performance, accessibility, FedRAMP package |

### GitHub Project Views to Configure

1. **Kanban Board** — columns: `Backlog | Ready | In Progress | In Review | Done`
2. **Roadmap** — group by Milestone, show start/end dates
3. **FedRAMP Tracker** — filter by label `fedramp`, group by control family
4. **Sprint Board** — filter by current sprint milestone

---

## FedRAMP Compliance Overview

This PoC targets **FedRAMP Moderate** baseline given:
- Government-operated deployment (TTB/Treasury)
- Processing of business-sensitive label and applicant data
- Potential for PII in Name & Address fields
- AI/ML processing of submitted documents

**Key control families in scope for a PoC:**

| Family | Code | Scope for this PoC |
|--------|------|--------------------|
| Access Control | AC | Role-based UI access; no anonymous submissions |
| Audit & Accountability | AU | Log all API calls, OCR requests, match decisions |
| Configuration Management | CM | Pinned dependencies, Docker image hashing, IaC |
| Identification & Authentication | IA | Auth before accessing results; session expiry |
| Incident Response | IR | Error handling; runbook for OCR failures |
| Risk Assessment | RA | Threat model; trust boundary documentation |
| System & Comms Protection | SC | TLS everywhere; in-memory-only data handling |
| System & Info Integrity | SI | SAST, SCA, DAST; no eval() or shell injection |
| System & Services Acquisition | SA | Third-party library review; vendor assessment |

> **Note:** Full ATO is out of scope for the PoC. The deliverable is a **completed FedRAMP documentation package** (SSP, data flow, POA&M) ready for hand-off to the agency's ISSO for formal assessment.

---

## Epic & Backlog Structure

Each epic below corresponds to a GitHub Milestone. Issues are written in GitHub issue format with acceptance criteria.

---

## EPIC 1 — Foundation & Infrastructure
**Milestone:** Phase 1 — Foundation | **Labels:** `epic`, `phase-1`  
**Goal:** A running, containerized skeleton that every subsequent issue builds on. Security controls established from day one — not bolted on at the end.

---

### ISSUE 1.1 — Initialize Monorepo Structure
**Labels:** `phase-1`, `devops`, `priority-critical`  
**Milestone:** Phase 1 — Foundation  

**Description:**  
Set up the repository layout so all teams can work in parallel without stepping on each other. The structure must support independent frontend and backend development with shared Docker orchestration.

**Acceptance Criteria:**
- [ ] Root contains `/frontend`, `/backend`, `/docs`, `/docker`, `/tests`, `.github/`
- [ ] `.gitignore` excludes `node_modules/`, `__pycache__/`, `.env`, `*.pyc`, label images
- [ ] `README.md` at root with one-command setup instructions
- [ ] `CODEOWNERS` file assigning review ownership per directory
- [ ] Branch protection enabled on `main`: require 1 approval + passing CI before merge

**FedRAMP Control:** CM-2 (Baseline Configuration), CM-6 (Configuration Settings)

---

### ISSUE 1.2 — Configure GitHub Actions CI Pipeline
**Labels:** `phase-1`, `devops`, `security`, `priority-critical`  
**Milestone:** Phase 1 — Foundation  

**Description:**  
Every push must trigger automated checks. This is the enforcement gate for code quality and security — nothing lands in `main` without passing.

**Acceptance Criteria:**
- [ ] `.github/workflows/ci.yml` runs on every PR and push to `main`
- [ ] Python backend: `pytest`, `bandit` (SAST), `pip-audit` (SCA)
- [ ] JS frontend: `eslint` with `eslint-plugin-security`, `npm audit`
- [ ] Docker: `docker build` succeeds, `trivy` image scan with no CRITICAL CVEs
- [ ] Status checks block merge on failure
- [ ] Secrets never logged; `ANTHROPIC_API_KEY` injected via GitHub Secrets only

**FedRAMP Control:** SI-3 (Malicious Code Protection), CM-3 (Configuration Change Control), SA-11 (Developer Testing)

---

### ISSUE 1.3 — Docker & Docker Compose Setup
**Labels:** `phase-1`, `devops`, `priority-critical`  
**Milestone:** Phase 1 — Foundation  

**Description:**  
The entire system must start with a single command. This is the deployment model for the government environment — IT hands the docker-compose file to a system admin.

**Acceptance Criteria:**
- [ ] `docker-compose.yml` starts frontend + backend + (optional) Redis with `docker-compose up`
- [ ] `Dockerfile` for backend: Python 3.11-slim, pinned dependency versions, non-root user
- [ ] `Dockerfile` for frontend: Node 20-alpine, multi-stage build, static files served via nginx
- [ ] All images use digest-pinned base images (e.g., `python:3.11-slim@sha256:...`)
- [ ] `.env.example` documents all required env vars; `.env` is gitignored
- [ ] `docker-compose up` produces a working app at `http://localhost:3000` within 60 seconds

**FedRAMP Control:** CM-7 (Least Functionality), SC-28 (Protection of Information at Rest)

---

### ISSUE 1.4 — FastAPI Backend Skeleton
**Labels:** `phase-1`, `backend`, `priority-critical`  
**Milestone:** Phase 1 — Foundation  

**Description:**  
Stand up the API with its full route surface defined — even if handlers return stubs. This unblocks frontend integration and establishes the contract.

**Acceptance Criteria:**
- [ ] `GET /health` returns `{status: "ok", version: "x.y.z"}`
- [ ] `POST /verify` accepts `{image: base64, application_data: {...}}`, returns stub
- [ ] `POST /verify/batch` accepts multipart form with image files + CSV, returns `{job_id}`
- [ ] `GET /jobs/{job_id}/status` returns batch progress
- [ ] `GET /jobs/{job_id}/results` returns completed results
- [ ] `GET /jobs/{job_id}/export` returns CSV file
- [ ] OpenAPI docs auto-generated at `/docs`
- [ ] Request/response models defined with Pydantic — no untyped dicts
- [ ] 413 returned for images > 20MB; 415 for non-image content types

**FedRAMP Control:** SI-10 (Information Input Validation), SC-8 (Transmission Confidentiality)

---

### ISSUE 1.5 — React Frontend Shell
**Labels:** `phase-1`, `frontend`, `priority-critical`  
**Milestone:** Phase 1 — Foundation  

**Description:**  
The UI shell with routing and layout established. Design system initialized with accessibility defaults so every component built on top inherits them.

**Acceptance Criteria:**
- [ ] Single-page app with React 18 + Vite
- [ ] Tailwind CSS configured with accessible color palette (WCAG AA contrast ratios)
- [ ] Pages: `/` (Upload), `/results/:sessionId` (Review), `/batch` (Batch Upload)
- [ ] Global error boundary prevents blank white screens
- [ ] Loading states defined for all async operations
- [ ] `<title>` and `<lang>` set correctly for screen readers
- [ ] Connects to backend via `VITE_API_URL` env var

**FedRAMP Control:** AC-17 (Remote Access — ensure no unauth'd access to results)

---

### ISSUE 1.6 — Draft System Security Plan (SSP)
**Labels:** `phase-1`, `fedramp`, `fedramp-ra`, `documentation`, `priority-critical`  
**Milestone:** Phase 1 — Foundation  

**Description:**  
The SSP is the primary FedRAMP artifact. It must be started in Phase 1 while the architecture is being built — not after. The ISSO cannot begin assessment without it.

**Acceptance Criteria:**
- [ ] `/docs/fedramp/SSP-draft.md` created with NIST 800-53r5 template structure
- [ ] System boundary diagram included (reference ADR-001 architecture diagram)
- [ ] Data types inventory: label images, application metadata, extracted fields, match results
- [ ] PII handling declared: Name & Address field classified as PII; ephemeral handling described
- [ ] System categorization justified: Moderate (C=M, I=M, A=M) per FIPS 199
- [ ] All external connections documented: Claude Vision API endpoint, Tesseract (local)
- [ ] Control families AC, AU, CM, IA, SC, SI mapped to implementation notes

**FedRAMP Control:** PL-2 (System Security Plan), RA-2 (Security Categorization)

---

### ISSUE 1.7 — Define Data Flow & Trust Boundary Documentation
**Labels:** `phase-1`, `fedramp`, `fedramp-sc`, `documentation`, `priority-high`  
**Milestone:** Phase 1 — Foundation  

**Description:**  
Formal data flow documentation for FedRAMP package. Auditors require this to assess what data crosses which boundaries and how it is protected.

**Acceptance Criteria:**
- [ ] `/docs/fedramp/DATA-FLOW.md` created
- [ ] All data flows documented: Reviewer → UI → API → OCR Engine → External API
- [ ] Trust boundaries explicitly labeled: internal (container network), external (vision API)
- [ ] Data classification at each boundary: image (Sensitive), extracted text (Sensitive), match results (Internal)
- [ ] Encryption in transit confirmed: HTTPS/TLS 1.2+ for all external calls
- [ ] No data-at-rest paths — confirmed ephemeral processing documented
- [ ] References ADR-001 data flow diagram

**FedRAMP Control:** SC-8 (Transmission Confidentiality and Integrity), AC-4 (Information Flow Enforcement)

---

## EPIC 2 — Core AI Intelligence
**Milestone:** Phase 2 — Core Intelligence | **Labels:** `epic`, `phase-2`  
**Goal:** A working OCR + matching pipeline that correctly extracts all 6 required label fields and applies the right matching rules for each.

---

### ISSUE 2.1 — Implement OCR Adapter (Claude Vision + Tesseract Fallback)
**Labels:** `phase-2`, `backend`, `ai-ml`, `priority-critical`  
**Milestone:** Phase 2 — Core Intelligence  

**Description:**  
The OCR adapter is the system's most critical component. It must work in the firewalled government environment by falling back to local Tesseract if the cloud API is unreachable.

**Acceptance Criteria:**
- [ ] `backend/ocr/adapter.py` — single `extract_fields(image_bytes) → ExtractedFields` interface
- [ ] Primary path: calls Claude Vision API with structured extraction prompt
- [ ] Fallback path: catches `ConnectionError` / `TimeoutError`, runs Tesseract locally
- [ ] Fallback activates within 3 seconds of first timeout — no infinite waits
- [ ] `ExtractedFields` dataclass contains: `brand`, `class_type`, `abv`, `net_contents`, `name_address`, `country_of_origin`, `government_warning`, `confidence_score`, `ocr_engine_used`
- [ ] API key loaded from env var only — never hardcoded
- [ ] Unit tests: mock API success, mock API timeout (triggers fallback), malformed image

**FedRAMP Control:** SA-9 (External System Services), SC-8 (Transmission Confidentiality)

---

### ISSUE 2.2 — Implement Image Quality Assessment
**Labels:** `phase-2`, `backend`, `ai-ml`, `priority-high`  
**Milestone:** Phase 2 — Core Intelligence  

**Description:**  
Real-world label photos have glare, angles, and obstructions. The system must assess quality and communicate it to the reviewer rather than silently returning bad results.

**Acceptance Criteria:**
- [ ] `backend/ocr/quality.py` returns `ImageQualityReport {score: 0–100, issues: []}`
- [ ] Detected issues: `low_resolution`, `excessive_glare`, `skewed_angle`, `partial_obstruction`, `blurry`
- [ ] OpenCV pre-processing applied: deskew, denoise, contrast enhancement
- [ ] Quality score attached to every `VerificationResult`
- [ ] If score < 40, result flagged with `low_confidence` warning in UI
- [ ] System does not reject images — it degrades gracefully and returns lower confidence scores
- [ ] Unit tests: pristine image (score > 80), simulated glare (score 40–70), very dark image (score < 40)

**FedRAMP Control:** SI-10 (Information Input Validation)

---

### ISSUE 2.3 — Implement Field Parser
**Labels:** `phase-2`, `backend`, `ai-ml`, `priority-critical`  
**Milestone:** Phase 2 — Core Intelligence  

**Description:**  
Raw OCR output must be parsed into the 6 structured fields required by TTB. The parser must handle OCR noise (spurious line breaks, merged characters) gracefully.

**Acceptance Criteria:**
- [ ] `backend/ocr/parser.py` maps raw OCR text to `ExtractedFields`
- [ ] Brand Name: extracted from first prominent text block
- [ ] Class/Type: extracted via keyword proximity ("VODKA", "WHISKEY", "ALE", etc.)
- [ ] ABV/Proof: regex for `XX% Alc. by Vol.` and `XX Proof` patterns
- [ ] Net Contents: regex for `XXXmL`, `XX fl oz`, `X L` with unit normalization
- [ ] Name & Address: extracted from bottom-of-label text block (TTB position convention)
- [ ] Country of Origin: "Product of X" / "Made in X" pattern matching
- [ ] Government Warning: extracted as full verbatim block starting with "GOVERNMENT WARNING"
- [ ] Unit tests for each field with realistic OCR output examples

**FedRAMP Control:** SI-10 (Information Input Validation)

---

### ISSUE 2.4 — Implement Fuzzy Matching Engine
**Labels:** `phase-2`, `backend`, `ai-ml`, `priority-critical`  
**Milestone:** Phase 2 — Core Intelligence  

**Description:**  
The matching engine compares extracted label fields against application data using per-field rules. Most fields use fuzzy matching; the Government Warning uses exact matching.

**Acceptance Criteria:**
- [ ] `backend/matching/engine.py` — `compare(extracted, application_data) → MatchReport`
- [ ] RapidFuzz `token_sort_ratio` used for: Brand (≥90%), Class/Type (≥85%), Name & Address (≥80%), Country of Origin (≥90%)
- [ ] Numeric tolerance for: ABV (±0.5%), Net Contents (±1% after unit normalization)
- [ ] Status per field: `MATCH` / `PARTIAL_MATCH` / `NO_MATCH`
- [ ] Overall status: `MATCH` (all fields match), `PARTIAL` (1+ partial), `FAIL` (1+ no-match)
- [ ] Discrepancy detail: for each failed field, return `{extracted: "...", expected: "...", score: N}`
- [ ] Unit tests: exact same input (all MATCH), minor variation (PARTIAL), completely wrong (NO MATCH)

**FedRAMP Control:** SI-10 (Information Input Validation)

---

### ISSUE 2.5 — Implement Government Warning Exact Validator
**Labels:** `phase-2`, `backend`, `priority-critical`  
**Milestone:** Phase 2 — Core Intelligence  

**Description:**  
The Government Warning is legally mandated verbatim text. Unlike other fields it must be an exact word-for-word match — no fuzzy tolerance. Formatting (ALL-CAPS prefix) must also be verified.

**Acceptance Criteria:**
- [ ] `backend/matching/exact_validator.py` validates Government Warning independently
- [ ] Word-for-word comparison after whitespace normalization (collapse runs of spaces/newlines)
- [ ] Verifies "GOVERNMENT WARNING" prefix is ALL-CAPS
- [ ] Returns: `{valid: bool, issues: [], extracted_text: "...", expected_text: "..."}`
- [ ] Issues list can contain: `WRONG_TEXT`, `MISSING_PREFIX`, `LOWERCASE_PREFIX`, `EXTRA_TEXT`, `MISSING_TEXT`
- [ ] Any issue → field status `NO_MATCH` regardless of similarity score
- [ ] Unit tests: correct warning (valid), lowercase prefix (invalid), wrong text (invalid), extra words appended (invalid)

**FedRAMP Control:** SI-7 (Software, Firmware, and Information Integrity)

---

### ISSUE 2.6 — Integrate SAST and Dependency Scanning
**Labels:** `phase-2`, `fedramp`, `fedramp-si`, `security`, `devops`, `priority-critical`  
**Milestone:** Phase 2 — Core Intelligence  

**Description:**  
FedRAMP SI-3 and SA-11 require automated code scanning. Must be integrated into CI so it runs on every PR — not as a manual step.

**Acceptance Criteria:**
- [ ] `bandit` (Python SAST) runs in CI; HIGH severity findings block merge
- [ ] `pip-audit` or `safety` runs in CI; known CVEs in dependencies block merge
- [ ] `eslint-plugin-security` runs in frontend CI; HIGH findings block merge
- [ ] `npm audit --audit-level=high` runs in frontend CI
- [ ] `trivy` Docker image scan runs in CI; CRITICAL CVEs block merge
- [ ] SAST results exported to GitHub Security tab (SARIF format)
- [ ] `/docs/fedramp/SAST-RESULTS.md` documents baseline findings and mitigations
- [ ] Suppressed findings have documented justification in `.bandit` or `.trivyignore`

**FedRAMP Control:** SI-3 (Malicious Code Protection), SA-11 (Developer Security Testing), RA-5 (Vulnerability Monitoring)

---

### ISSUE 2.7 — Implement Structured Audit Logging
**Labels:** `phase-2`, `fedramp`, `fedramp-au`, `backend`, `priority-critical`  
**Milestone:** Phase 2 — Core Intelligence  

**Description:**  
FedRAMP AU controls require all significant system events to be logged with enough detail for forensic reconstruction. Logs must never contain the label images themselves or raw PII.

**Acceptance Criteria:**
- [ ] Structured JSON logs (via `structlog` or `python-json-logger`) for all API endpoints
- [ ] Each log entry includes: `timestamp`, `request_id`, `endpoint`, `status_code`, `duration_ms`, `session_id`, `ocr_engine_used`
- [ ] Log fields that must NOT appear: `image_bytes`, `base64_data`, raw Name & Address value
- [ ] Logged events: API request received, OCR started, OCR completed (+ engine used), match completed, error conditions, session expiry
- [ ] Log level configurable via env var (`LOG_LEVEL=INFO`)
- [ ] Logs written to stdout (Docker best practice) — not to files inside container
- [ ] Unit test: assert PII fields are absent from log output

**FedRAMP Control:** AU-2 (Event Logging), AU-3 (Content of Audit Records), AU-9 (Protection of Audit Information)

---

## EPIC 3 — Batch Processing & Review UI
**Milestone:** Phase 3 — Batch & UI | **Labels:** `epic`, `phase-3`  
**Goal:** Reviewers can upload 200–300 labels at once, track progress in real time, and review results in a clean side-by-side interface.

---

### ISSUE 3.1 — Implement Batch Orchestrator
**Labels:** `phase-3`, `backend`, `priority-critical`  
**Milestone:** Phase 3 — Batch & UI  

**Description:**  
Parallel processing of 200–300 labels using Python asyncio. Must maintain ≤5s per label average while not crashing under load.

**Acceptance Criteria:**
- [ ] `backend/batch/orchestrator.py` — `start_batch(job_id, label_pairs[]) → AsyncIterator[Progress]`
- [ ] `asyncio.gather` with configurable concurrency limit (default: 10 workers)
- [ ] Per-label progress events: `{job_id, completed, total, latest: VerificationResult}`
- [ ] Job state stored in `backend/batch/store.py` (in-memory dict keyed by `job_id`)
- [ ] Completed jobs retained for session duration; cleared on app restart
- [ ] Malformed images in batch do not abort entire batch — they produce an error result for that label
- [ ] Load test: 300 labels processed with ≤5s average, no worker crashes

**FedRAMP Control:** SI-12 (Information Management and Retention — ephemeral only)

---

### ISSUE 3.2 — Implement SSE Progress Streaming
**Labels:** `phase-3`, `backend`, `frontend`, `priority-high`  
**Milestone:** Phase 3 — Batch & UI  

**Description:**  
The reviewer needs real-time feedback when processing 300 labels. Server-Sent Events (SSE) provide a simple, reliable push channel without WebSocket complexity.

**Acceptance Criteria:**
- [ ] `GET /jobs/{job_id}/stream` returns `text/event-stream` response
- [ ] Events emitted: `progress` (every label complete), `complete` (batch done), `error` (label failed)
- [ ] Frontend `EventSource` reconnects automatically if connection drops
- [ ] Progress bar in UI updates per event: "Processed 47 of 300 labels"
- [ ] Most recent 5 results shown as they complete (live feed)
- [ ] Stream closes cleanly when batch is complete

**FedRAMP Control:** SC-8 (Transmission Confidentiality)

---

### ISSUE 3.3 — Build Single-Label Review UI
**Labels:** `phase-3`, `frontend`, `priority-critical`  
**Milestone:** Phase 3 — Batch & UI  

**Description:**  
The primary reviewer workflow: upload one label + application data, see results side-by-side. Must work for a 73-year-old user with no training.

**Acceptance Criteria:**
- [ ] Upload area: large drag-and-drop zone with "or click to browse" fallback
- [ ] Application data entry: text fields for each of the 6 required fields (no free-text JSON)
- [ ] Results panel: two columns — "Label Says" vs "Application Says" — per field
- [ ] Status indicators: ✅ green (MATCH), ⚠️ yellow (PARTIAL), ❌ red (NO MATCH)
- [ ] Confidence score shown as percentage bar per field
- [ ] Government Warning displayed as its own section with exact-match indicator
- [ ] Image quality warning banner if score < 40
- [ ] "Export CSV" button at bottom of results
- [ ] No hidden menus, no tooltips required to understand the UI
- [ ] Passes manual usability test: a non-technical user completes a verification in <2 minutes

**FedRAMP Control:** AC-3 (Access Enforcement — results visible only to uploader session)

---

### ISSUE 3.4 — Build Batch Upload & Progress UI
**Labels:** `phase-3`, `frontend`, `priority-critical`  
**Milestone:** Phase 3 — Batch & UI  

**Description:**  
Bulk workflow for processing 200–300 labels. The reviewer needs to track progress without needing to stare at a loading spinner for 25 minutes.

**Acceptance Criteria:**
- [ ] Batch upload page: ZIP upload for images + CSV upload for application data
- [ ] CSV format validated client-side before submit: show column mapping errors before upload starts
- [ ] After submit: progress bar + counter ("47 of 300 complete")
- [ ] Live results feed: most recent 10 completed labels shown as they finish
- [ ] On completion: summary card — total MATCH / PARTIAL / FAIL counts
- [ ] "Download Full Report" button exports Excel with one row per label
- [ ] "Restart" button clears session without page reload

**FedRAMP Control:** SI-10 (Information Input Validation — CSV column validation)

---

### ISSUE 3.5 — Implement In-Memory Session Store & Export
**Labels:** `phase-3`, `backend`, `priority-high`  
**Milestone:** Phase 3 — Batch & UI  

**Description:**  
Results are held in memory for the duration of the reviewer's session. No disk writes, no database. The export endpoint converts the session data to CSV or Excel for the reviewer to download and retain.

**Acceptance Criteria:**
- [ ] `backend/store/session_store.py` — dict-backed store keyed by `session_id`
- [ ] Sessions expire after 4 hours of inactivity (configurable via env var)
- [ ] `GET /jobs/{job_id}/export?format=csv` returns RFC 4180-compliant CSV
- [ ] `GET /jobs/{job_id}/export?format=xlsx` returns Excel with formatted headers and color-coded status cells
- [ ] Export includes: label filename, each extracted field, each match status, confidence scores, overall status
- [ ] Memory usage capped: single label result ~2KB; 300-label batch ~600KB — well within bounds
- [ ] Unit test: store → retrieve → export roundtrip

**FedRAMP Control:** SI-12 (Information Management and Retention), SC-28 (Protection of Information at Rest — confirmed no disk write)

---

### ISSUE 3.6 — Implement Input Validation & Sanitization
**Labels:** `phase-3`, `fedramp`, `fedramp-si`, `backend`, `security`, `priority-critical`  
**Milestone:** Phase 3 — Batch & UI  

**Description:**  
All inputs entering the API must be validated and sanitized. This is both a security control and a reliability requirement — bad inputs should never crash a worker.

**Acceptance Criteria:**
- [ ] Image uploads: validate MIME type server-side (not just extension); reject non-image content
- [ ] Image size limit: 20MB per image; 500MB per batch ZIP
- [ ] CSV application data: validate required column headers on ingest; reject unknown column names
- [ ] All string fields: strip leading/trailing whitespace; max length enforced (brand: 255 chars, etc.)
- [ ] No `eval()`, `exec()`, `subprocess` with user-controlled input anywhere in codebase
- [ ] SQLi irrelevant (no DB), but XSS prevented: all user data HTML-escaped in React
- [ ] Pydantic models enforce types on all API request bodies
- [ ] Fuzzing test: 20 malformed inputs; none crash the server

**FedRAMP Control:** SI-10 (Information Input Validation), SI-16 (Memory Protection)

---

### ISSUE 3.7 — Implement Session Authentication
**Labels:** `phase-3`, `fedramp`, `fedramp-ac`, `fedramp-ia`, `backend`, `frontend`, `priority-high`  
**Milestone:** Phase 3 — Batch & UI  

**Description:**  
Results must not be accessible to unauthenticated users or to users of other sessions. For the PoC, a simple session token model is sufficient — full OAuth/PIV integration is out of scope.

**Acceptance Criteria:**
- [ ] On first visit, browser receives a signed `session_id` cookie (HttpOnly, Secure, SameSite=Strict)
- [ ] All `/jobs/*` endpoints require the session cookie; return 403 if absent or invalid
- [ ] Session IDs are cryptographically random (secrets.token_urlsafe(32))
- [ ] Sessions expire server-side after 4 hours; cookie max-age matches
- [ ] Results for `job_id` accessible only to the session that created them
- [ ] No "admin" view that lists all sessions or all jobs (not needed for PoC)
- [ ] `/docs/fedramp/SESSION-MANAGEMENT.md` documents this control implementation

**FedRAMP Control:** AC-3 (Access Enforcement), IA-2 (Identification and Authentication), SC-23 (Session Authenticity)

---

## EPIC 4 — Hardening & ATO Prep
**Milestone:** Phase 4 — Hardening & ATO Prep | **Labels:** `epic`, `phase-4`  
**Goal:** Production-ready reliability, WCAG AA accessibility, and a complete FedRAMP documentation package ready for ISSO hand-off.

---

### ISSUE 4.1 — OpenCV Image Pre-Processing Pipeline
**Labels:** `phase-4`, `backend`, `ai-ml`, `priority-high`  
**Milestone:** Phase 4 — Hardening & ATO Prep  

**Description:**  
Improve OCR accuracy on real-world label photos by pre-processing images before sending to the OCR engine. This is especially important for the Tesseract fallback path.

**Acceptance Criteria:**
- [ ] `backend/ocr/preprocessor.py` runs before OCR adapter: deskew → denoise → sharpen → contrast
- [ ] OpenCV operations: `getRotationMatrix2D`, `fastNlMeansDenoisingColored`, `equalizeHist`
- [ ] Pre-processing adds ≤0.5s to total processing time
- [ ] Original image never modified — preprocessing works on a copy
- [ ] A/B test: 20 real-world label samples — show quality score improvement with vs. without pre-processing
- [ ] Pre-processing skipped if image quality score already > 80 (avoid degrading good images)

**FedRAMP Control:** SI-10 (Information Input Validation)

---

### ISSUE 4.2 — Load Testing & Performance Validation
**Labels:** `phase-4`, `testing`, `priority-critical`  
**Milestone:** Phase 4 — Hardening & ATO Prep  

**Description:**  
The system must demonstrably meet the ≤5s per label requirement under realistic batch conditions. Results must be documented in the FedRAMP package as evidence of availability controls.

**Acceptance Criteria:**
- [ ] Locust or pytest-benchmark test script in `/tests/load/`
- [ ] Test scenario: 300 labels submitted in batch; all processed; measure per-label latency
- [ ] P50 latency ≤ 5s, P95 ≤ 8s, P99 ≤ 12s — documented in results
- [ ] Zero worker crashes or uncaught exceptions during 300-label run
- [ ] Memory usage stays below 2GB during batch (monitored via `psutil`)
- [ ] Test runs against both OCR paths: cloud API and Tesseract fallback
- [ ] `/docs/LOAD-TEST-RESULTS.md` captures results, configuration, and environment details

**FedRAMP Control:** AU-14 (Session Audit), CP-10 (System Recovery and Reconstitution)

---

### ISSUE 4.3 — Accessibility Audit & Remediation (WCAG AA)
**Labels:** `phase-4`, `frontend`, `accessibility`, `priority-critical`  
**Milestone:** Phase 4 — Hardening & ATO Prep  

**Description:**  
Federal applications are required to meet Section 508 (WCAG 2.1 AA). The UI was also specified to work for a 73-year-old user with limited technical experience — accessibility is both a compliance and usability requirement.

**Acceptance Criteria:**
- [ ] `axe-core` automated scan: zero WCAG AA violations on all 3 pages
- [ ] Manual keyboard navigation: all functionality reachable without mouse
- [ ] Tab order logical; focus indicator visible (min 3px outline)
- [ ] All images have descriptive `alt` text
- [ ] Color is never the only indicator of status (icons + text used alongside colors)
- [ ] Minimum font size 16px body, 14px secondary
- [ ] All form inputs have associated `<label>` elements
- [ ] Error messages announced to screen readers via `aria-live` regions
- [ ] Tested with NVDA or VoiceOver: upload, verify, and export flow completable
- [ ] `/docs/ACCESSIBILITY-REPORT.md` documents audit results and any accepted exceptions

**FedRAMP Control:** PL-8 (Security and Privacy Architectures — inclusive design)

---

### ISSUE 4.4 — Comprehensive Error Handling & Graceful Degradation
**Labels:** `phase-4`, `backend`, `frontend`, `priority-high`  
**Milestone:** Phase 4 — Hardening & ATO Prep  

**Description:**  
The system must never show a blank screen, crash silently, or leave a reviewer without actionable information. Every error condition must produce a useful message.

**Acceptance Criteria:**
- [ ] Backend: global FastAPI exception handler returns structured `{error, message, request_id}` — never raw stack traces
- [ ] OCR API timeout: returns result with `ocr_engine: "tesseract"` and `confidence_score` adjusted down
- [ ] Image completely unreadable: returns result with `status: "ERROR"`, `message: "Image quality too low to extract any fields"` — does not crash
- [ ] Batch item failure: failed label gets error result; remaining labels continue processing
- [ ] Frontend: global React error boundary shows "Something went wrong — your session is still active" with retry button
- [ ] Network error during SSE stream: UI shows "Reconnecting..." and EventSource reconnects
- [ ] All error messages use plain language — no stack traces or technical jargon shown to users

**FedRAMP Control:** SI-17 (Fail-Safe Procedures), IR-8 (Incident Response Plan alignment)

---

### ISSUE 4.5 — Complete FedRAMP Documentation Package
**Labels:** `phase-4`, `fedramp`, `documentation`, `priority-critical`  
**Milestone:** Phase 4 — Hardening & ATO Prep  

**Description:**  
Assemble the complete documentation package ready for hand-off to the TTB ISSO. This is the deliverable that enables the agency to pursue formal ATO if the PoC is approved for production.

**Acceptance Criteria:**
- [ ] `/docs/fedramp/SSP-final.md` — complete with all control implementations documented
- [ ] `/docs/fedramp/POAM.md` — Plan of Action & Milestones listing known gaps with remediation timeline
- [ ] `/docs/fedramp/DATA-FLOW-final.md` — finalized with actual endpoint URLs and confirmed encryption posture
- [ ] `/docs/fedramp/SAST-RESULTS.md` — final scan results with all findings addressed or mitigated
- [ ] `/docs/fedramp/CONTROL-MATRIX.xlsx` — NIST 800-53r5 Moderate baseline; each control marked: Implemented / Planned / Not Applicable / Inherited
- [ ] `/docs/fedramp/INCIDENT-RESPONSE-PLAN.md` — procedures for OCR failures, data exposure events, and availability incidents
- [ ] `/docs/fedramp/SYSTEM-BOUNDARY.png` — finalized from ADR-001 architecture diagram
- [ ] Peer-reviewed by at least one team member not involved in implementation

**FedRAMP Control:** PL-2 (System Security Plan), CA-5 (Plan of Action and Milestones), CA-7 (Continuous Monitoring)

---

### ISSUE 4.6 — Threat Model Documentation
**Labels:** `phase-4`, `fedramp`, `fedramp-ra`, `security`, `priority-high`  
**Milestone:** Phase 4 — Hardening & ATO Prep  

**Description:**  
FedRAMP RA controls require a documented threat model. Using STRIDE methodology for a PoC scope is sufficient and maps cleanly to the NIST control framework.

**Acceptance Criteria:**
- [ ] `/docs/fedramp/THREAT-MODEL.md` created using STRIDE framework
- [ ] Threat categories analyzed: Spoofing (session), Tampering (label image), Repudiation (audit logs), Info Disclosure (OCR data), DoS (batch load), Elevation of Privilege (API auth)
- [ ] Each threat mapped to: likelihood (L/M/H), impact (L/M/H), mitigating control, residual risk
- [ ] Top 3 risks called out with owner and mitigation timeline
- [ ] Data flow diagram annotated with trust boundaries (reference ADR-001)
- [ ] Review sign-off by project lead

**FedRAMP Control:** RA-3 (Risk Assessment), RA-5 (Vulnerability Monitoring and Scanning)

---

### ISSUE 4.7 — Final README & Deployment Guide
**Labels:** `phase-4`, `documentation`, `devops`, `priority-high`  
**Milestone:** Phase 4 — Hardening & ATO Prep  

**Description:**  
A system admin with no prior knowledge of the application must be able to install and run it using only the README.

**Acceptance Criteria:**
- [ ] `README.md` covers: prerequisites, one-command setup, env var reference, how to run tests, how to access the app
- [ ] `/docs/DEPLOYMENT-GUIDE.md` covers: network requirements (firewall rules), Docker install, running in air-gapped mode, backup/restore (N/A — ephemeral), updating the application
- [ ] Firewall allowlist explicitly documented: single outbound hostname for Claude Vision API (with port and protocol)
- [ ] "Air-gapped mode" instructions: set `OCR_MODE=local` to force Tesseract, skip API key requirement
- [ ] Tested: a team member not involved in dev follows the guide and successfully runs the app from scratch

**FedRAMP Control:** CM-6 (Configuration Settings), CM-7 (Least Functionality)

---

## FedRAMP Control Coverage Matrix

| NIST Control | Family | Phase | Implemented By |
|-------------|--------|-------|----------------|
| AC-3 | Access Control | 3 | Session auth (Issue 3.7) + results isolation |
| AC-4 | Information Flow | 1 | Data flow doc + in-memory only processing |
| AC-17 | Remote Access | 1 | HTTPS enforced; no unauthenticated access |
| AU-2 | Event Logging | 2 | Structured audit logging (Issue 2.7) |
| AU-3 | Audit Content | 2 | Request ID, timestamps, session ID logged |
| AU-9 | Audit Protection | 2 | Logs to stdout → container orchestrator; no user write access |
| CA-5 | POA&M | 4 | FedRAMP doc package (Issue 4.5) |
| CA-7 | Continuous Monitoring | 4 | CI SAST/SCA on every PR |
| CM-2 | Baseline Config | 1 | Pinned Docker images + dependency lock files |
| CM-3 | Change Control | 1 | GitHub branch protection + required CI |
| CM-6 | Config Settings | 1, 4 | Env var documentation; no hardcoded config |
| CM-7 | Least Functionality | 1 | Docker non-root; minimal base image |
| IA-2 | Identification & Auth | 3 | Session token authentication |
| IR-8 | Incident Response | 4 | Incident response plan (Issue 4.5) |
| PL-2 | Security Plan | 1, 4 | SSP drafted Phase 1; finalized Phase 4 |
| RA-2 | Security Categorization | 1 | FIPS 199 categorization in SSP |
| RA-3 | Risk Assessment | 4 | Threat model (Issue 4.6) |
| RA-5 | Vulnerability Scanning | 2 | SAST + SCA in CI (Issue 2.6) |
| SA-9 | External Services | 2 | Claude Vision API documented + fallback |
| SA-11 | Developer Testing | 1 | SAST integrated in CI pipeline |
| SC-8 | Transmission Integrity | 1, 2 | TLS 1.2+ for all external calls |
| SC-23 | Session Authenticity | 3 | HttpOnly/Secure/SameSite cookies |
| SC-28 | Data at Rest | 1, 3 | No disk writes confirmed; in-memory only |
| SI-3 | Malicious Code | 2 | Bandit + trivy + npm audit in CI |
| SI-7 | Integrity | 2 | Government Warning exact validator |
| SI-10 | Input Validation | 1, 2, 3 | Pydantic models + MIME validation + CSV validation |
| SI-12 | Info Retention | 3 | 4-hour session expiry; no persistence |
| SI-16 | Memory Protection | 3 | No eval/exec; Pydantic enforces types |
| SI-17 | Fail-Safe | 4 | Graceful degradation + error handling |

---

## Sprint Summary

| Sprint | Epic | Issues | FedRAMP Issues | Deliverable |
|--------|------|--------|----------------|-------------|
| Week 1 | Foundation | 1.1–1.5 | 1.6, 1.7 | Running containerized skeleton + SSP draft |
| Week 2 | Core Intelligence | 2.1–2.5 | 2.6, 2.7 | Working OCR + matching pipeline |
| Week 3 | Batch & UI | 3.1–3.5 | 3.6, 3.7 | Full batch workflow + reviewer UI |
| Week 4 | Hardening & ATO | 4.1–4.4 | 4.5, 4.6, 4.7 | Production-ready app + FedRAMP package |

**Total Issues:** 28 (21 engineering + 7 FedRAMP-primary)  
**FedRAMP-tagged issues across all phases:** 13
