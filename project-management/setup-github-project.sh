#!/usr/bin/env bash
# =============================================================================
# setup-github-project.sh
# Creates all labels, milestones, and issues for the Alcohol Label Verification
# PoC project in GitHub using the GitHub CLI (gh).
#
# Prerequisites:
#   - GitHub CLI installed: https://cli.github.com/
#   - Authenticated: gh auth login
#   - Run from inside your cloned repository, OR set REPO below
#
# Usage:
#   chmod +x setup-github-project.sh
#   ./setup-github-project.sh
#
# To target a specific repo (if not running from inside it):
#   REPO="owner/repo-name" ./setup-github-project.sh
# =============================================================================

set -euo pipefail

REPO="${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")}"

if [[ -z "$REPO" ]]; then
  echo "❌ Could not detect repo. Set REPO=owner/repo-name and re-run."
  exit 1
fi

echo "🚀 Setting up GitHub Project for: $REPO"
echo ""

# =============================================================================
# 1. CREATE LABELS
# =============================================================================
echo "🏷️  Creating labels..."

create_label() {
  local name="$1" color="$2" description="$3"
  gh label create "$name" --color "$color" --description "$description" --repo "$REPO" --force 2>/dev/null && \
    echo "  ✅ $name" || echo "  ⚠️  $name (already exists or failed)"
}

# Phase labels
create_label "epic"              "7B2D8B" "Parent epic grouping"
create_label "phase-1"           "0075CA" "Phase 1: Foundation & Infrastructure"
create_label "phase-2"           "00B4D8" "Phase 2: Core AI Intelligence"
create_label "phase-3"           "0077B6" "Phase 3: Batch Processing & UI"
create_label "phase-4"           "023E8A" "Phase 4: Hardening & ATO Prep"

# FedRAMP control family labels
create_label "fedramp"           "B00020" "FedRAMP compliance work"
create_label "fedramp-ac"        "D62839" "Access Control (AC)"
create_label "fedramp-au"        "D62839" "Audit & Accountability (AU)"
create_label "fedramp-cm"        "D62839" "Configuration Management (CM)"
create_label "fedramp-ia"        "D62839" "Identification & Authentication (IA)"
create_label "fedramp-sc"        "D62839" "System & Comms Protection (SC)"
create_label "fedramp-si"        "D62839" "System & Information Integrity (SI)"
create_label "fedramp-ra"        "D62839" "Risk Assessment (RA)"
create_label "fedramp-sa"        "D62839" "System & Services Acquisition (SA)"

# Engineering domain labels
create_label "backend"           "E36209" "Backend / FastAPI work"
create_label "frontend"          "0E8A16" "UI / React work"
create_label "devops"            "6F42C1" "Infrastructure / Docker / CI"
create_label "ai-ml"             "F9C513" "OCR / ML / Vision work"
create_label "security"          "B60205" "Security controls"
create_label "testing"           "FBCA04" "Testing & QA"
create_label "documentation"     "0075CA" "Docs, ADRs, runbooks"
create_label "accessibility"     "5319E7" "WCAG / a11y work"

# Priority labels
create_label "priority-critical" "B60205" "Must-have, blocks release"
create_label "priority-high"     "E4E669" "High value / high risk"
create_label "priority-medium"   "0E8A16" "Standard backlog"
create_label "priority-low"      "C2E0C6" "Nice-to-have"

# Status labels
create_label "blocked"           "E11D48" "Waiting on dependency"
create_label "needs-review"      "6366F1" "PR or design needs review"

echo ""

# =============================================================================
# 2. CREATE MILESTONES
# =============================================================================
echo "🗓️  Creating milestones..."

# Calculate dates relative to today (adjust as needed)
WEEK1=$(date -d "+7 days"  "+%Y-%m-%dT00:00:00Z" 2>/dev/null || date -v+7d "+%Y-%m-%dT00:00:00Z")
WEEK2=$(date -d "+14 days" "+%Y-%m-%dT00:00:00Z" 2>/dev/null || date -v+14d "+%Y-%m-%dT00:00:00Z")
WEEK3=$(date -d "+21 days" "+%Y-%m-%dT00:00:00Z" 2>/dev/null || date -v+21d "+%Y-%m-%dT00:00:00Z")
WEEK4=$(date -d "+28 days" "+%Y-%m-%dT00:00:00Z" 2>/dev/null || date -v+28d "+%Y-%m-%dT00:00:00Z")

create_milestone() {
  local title="$1" due="$2" desc="$3"
  gh api repos/$REPO/milestones \
    --method POST \
    --field title="$title" \
    --field due_on="$due" \
    --field description="$desc" \
    --silent 2>/dev/null && echo "  ✅ $title" || echo "  ⚠️  $title (may already exist)"
}

create_milestone "Phase 1 — Foundation"          "$WEEK1" "Monorepo, Docker, API skeleton, security baseline, SSP draft"
create_milestone "Phase 2 — Core Intelligence"   "$WEEK2" "OCR adapter, field parser, fuzzy/exact matching, audit logging"
create_milestone "Phase 3 — Batch & UI"          "$WEEK3" "Batch orchestrator, review interface, session auth, export"
create_milestone "Phase 4 — Hardening & ATO Prep" "$WEEK4" "Performance, accessibility, FedRAMP documentation package"

echo ""

# =============================================================================
# 3. HELPER: get milestone number by title
# =============================================================================
get_milestone_number() {
  gh api repos/$REPO/milestones --jq ".[] | select(.title == \"$1\") | .number"
}

# =============================================================================
# 4. CREATE ISSUES
# =============================================================================
echo "📋  Creating issues..."

create_issue() {
  local title="$1" milestone_name="$2" labels="$3" body="$4"
  local milestone_num
  milestone_num=$(get_milestone_number "$milestone_name")
  gh issue create \
    --repo "$REPO" \
    --title "$title" \
    --milestone "$milestone_num" \
    --label "$labels" \
    --body "$body" \
    --silent && echo "  ✅ $title" || echo "  ❌ Failed: $title"
}

# ── EPIC 1 ──────────────────────────────────────────────────────────────────
create_issue \
  "EPIC 1 — Foundation & Infrastructure" \
  "Phase 1 — Foundation" \
  "epic,phase-1" \
  "## Goal
A running containerized skeleton that every subsequent issue builds on. Security controls established from day one.

### Child Issues
- [ ] Initialize Monorepo Structure
- [ ] Configure GitHub Actions CI Pipeline
- [ ] Docker & Docker Compose Setup
- [ ] FastAPI Backend Skeleton
- [ ] React Frontend Shell
- [ ] Draft System Security Plan (SSP)
- [ ] Define Data Flow & Trust Boundary Documentation"

create_issue \
  "Initialize Monorepo Structure" \
  "Phase 1 — Foundation" \
  "phase-1,devops,priority-critical" \
  "## Description
Set up the repository layout so all teams can work in parallel without stepping on each other.

## Acceptance Criteria
- [ ] Root contains \`/frontend\`, \`/backend\`, \`/docs\`, \`/docker\`, \`/tests\`, \`.github/\`
- [ ] \`.gitignore\` excludes \`node_modules/\`, \`__pycache__/\`, \`.env\`, \`*.pyc\`, label images
- [ ] \`README.md\` at root with one-command setup instructions
- [ ] \`CODEOWNERS\` file assigning review ownership per directory
- [ ] Branch protection enabled on \`main\`: require 1 approval + passing CI before merge

## FedRAMP Controls
CM-2 (Baseline Configuration), CM-6 (Configuration Settings)"

create_issue \
  "Configure GitHub Actions CI Pipeline" \
  "Phase 1 — Foundation" \
  "phase-1,devops,security,fedramp,fedramp-si,priority-critical" \
  "## Description
Every push must trigger automated checks. Enforcement gate for code quality and security — nothing lands in \`main\` without passing.

## Acceptance Criteria
- [ ] \`.github/workflows/ci.yml\` runs on every PR and push to \`main\`
- [ ] Python backend: \`pytest\`, \`bandit\` (SAST), \`pip-audit\` (SCA)
- [ ] JS frontend: \`eslint\` with \`eslint-plugin-security\`, \`npm audit\`
- [ ] Docker: \`docker build\` succeeds, \`trivy\` image scan with no CRITICAL CVEs
- [ ] Status checks block merge on failure
- [ ] Secrets never logged; \`ANTHROPIC_API_KEY\` injected via GitHub Secrets only
- [ ] SARIF results exported to GitHub Security tab

## FedRAMP Controls
SI-3 (Malicious Code Protection), CM-3 (Configuration Change Control), SA-11 (Developer Testing)"

create_issue \
  "Docker & Docker Compose Setup" \
  "Phase 1 — Foundation" \
  "phase-1,devops,priority-critical" \
  "## Description
The entire system must start with a single command for deployment in the government environment.

## Acceptance Criteria
- [ ] \`docker-compose.yml\` starts frontend + backend with \`docker-compose up\`
- [ ] \`Dockerfile\` for backend: Python 3.11-slim, pinned dependency versions, non-root user
- [ ] \`Dockerfile\` for frontend: Node 20-alpine, multi-stage build, static files via nginx
- [ ] All images use digest-pinned base images
- [ ] \`.env.example\` documents all required env vars; \`.env\` is gitignored
- [ ] \`docker-compose up\` produces working app at \`http://localhost:3000\` within 60 seconds

## FedRAMP Controls
CM-7 (Least Functionality), SC-28 (Protection of Information at Rest)"

create_issue \
  "FastAPI Backend Skeleton" \
  "Phase 1 — Foundation" \
  "phase-1,backend,priority-critical" \
  "## Description
Stand up the API with its full route surface defined — even if handlers return stubs. Unblocks frontend integration.

## Acceptance Criteria
- [ ] \`GET /health\` returns \`{status: ok, version}\`
- [ ] \`POST /verify\` accepts \`{image: base64, application_data}\`, returns stub
- [ ] \`POST /verify/batch\` accepts multipart form; returns \`{job_id}\`
- [ ] \`GET /jobs/{job_id}/status\` returns batch progress
- [ ] \`GET /jobs/{job_id}/results\` returns completed results
- [ ] \`GET /jobs/{job_id}/export\` returns CSV file
- [ ] OpenAPI docs auto-generated at \`/docs\`
- [ ] Request/response models defined with Pydantic — no untyped dicts
- [ ] 413 for images > 20MB; 415 for non-image content types

## FedRAMP Controls
SI-10 (Information Input Validation), SC-8 (Transmission Confidentiality)"

create_issue \
  "React Frontend Shell" \
  "Phase 1 — Foundation" \
  "phase-1,frontend,priority-critical" \
  "## Description
UI shell with routing and layout. Design system initialized with accessibility defaults.

## Acceptance Criteria
- [ ] Single-page app with React 18 + Vite
- [ ] Tailwind CSS with accessible color palette (WCAG AA contrast)
- [ ] Pages: \`/\` (Upload), \`/results/:sessionId\` (Review), \`/batch\` (Batch Upload)
- [ ] Global error boundary prevents blank white screens
- [ ] Loading states defined for all async operations
- [ ] \`<title>\` and \`<lang>\` set correctly for screen readers
- [ ] Connects to backend via \`VITE_API_URL\` env var

## FedRAMP Controls
AC-17 (Remote Access)"

create_issue \
  "Draft System Security Plan (SSP)" \
  "Phase 1 — Foundation" \
  "phase-1,fedramp,fedramp-ra,documentation,priority-critical" \
  "## Description
The SSP is the primary FedRAMP artifact. Must be started in Phase 1 while architecture is being built.

## Acceptance Criteria
- [ ] \`/docs/fedramp/SSP-draft.md\` with NIST 800-53r5 template structure
- [ ] System boundary diagram included (reference ADR-001)
- [ ] Data types inventory: label images, application metadata, extracted fields, match results
- [ ] PII handling declared: Name & Address field classified as PII; ephemeral handling described
- [ ] System categorization: Moderate (C=M, I=M, A=M) per FIPS 199
- [ ] All external connections documented: Claude Vision API, Tesseract (local)
- [ ] Control families AC, AU, CM, IA, SC, SI mapped to implementation notes

## FedRAMP Controls
PL-2 (System Security Plan), RA-2 (Security Categorization)"

create_issue \
  "Define Data Flow & Trust Boundary Documentation" \
  "Phase 1 — Foundation" \
  "phase-1,fedramp,fedramp-sc,documentation,priority-high" \
  "## Description
Formal data flow documentation for FedRAMP package. Auditors require this to assess what data crosses which boundaries.

## Acceptance Criteria
- [ ] \`/docs/fedramp/DATA-FLOW.md\` created
- [ ] All data flows documented: Reviewer → UI → API → OCR Engine → External API
- [ ] Trust boundaries explicitly labeled: internal (container network), external (vision API)
- [ ] Data classification at each boundary
- [ ] Encryption in transit confirmed: HTTPS/TLS 1.2+ for all external calls
- [ ] No data-at-rest paths confirmed
- [ ] References ADR-001 data flow diagram

## FedRAMP Controls
SC-8 (Transmission Confidentiality and Integrity), AC-4 (Information Flow Enforcement)"

# ── EPIC 2 ──────────────────────────────────────────────────────────────────
create_issue \
  "EPIC 2 — Core AI Intelligence" \
  "Phase 2 — Core Intelligence" \
  "epic,phase-2" \
  "## Goal
A working OCR + matching pipeline that correctly extracts all 6 required label fields and applies the right matching rules.

### Child Issues
- [ ] Implement OCR Adapter (Claude Vision + Tesseract Fallback)
- [ ] Implement Image Quality Assessment
- [ ] Implement Field Parser
- [ ] Implement Fuzzy Matching Engine
- [ ] Implement Government Warning Exact Validator
- [ ] Integrate SAST and Dependency Scanning
- [ ] Implement Structured Audit Logging"

create_issue \
  "Implement OCR Adapter (Claude Vision + Tesseract Fallback)" \
  "Phase 2 — Core Intelligence" \
  "phase-2,backend,ai-ml,priority-critical" \
  "## Description
The OCR adapter is the system's most critical component. Must work in firewalled environments via Tesseract fallback.

## Acceptance Criteria
- [ ] \`backend/ocr/adapter.py\` — single \`extract_fields(image_bytes) → ExtractedFields\` interface
- [ ] Primary path: calls Claude Vision API with structured extraction prompt
- [ ] Fallback path: catches \`ConnectionError\`/\`TimeoutError\`, runs Tesseract locally
- [ ] Fallback activates within 3 seconds of first timeout
- [ ] \`ExtractedFields\` contains all 7 fields + \`confidence_score\` + \`ocr_engine_used\`
- [ ] API key loaded from env var only — never hardcoded
- [ ] Unit tests: mock API success, mock API timeout (triggers fallback), malformed image

## FedRAMP Controls
SA-9 (External System Services), SC-8 (Transmission Confidentiality)"

create_issue \
  "Implement Image Quality Assessment" \
  "Phase 2 — Core Intelligence" \
  "phase-2,backend,ai-ml,priority-high" \
  "## Description
Assess image quality and pre-process with OpenCV. Return confidence scores rather than silently failing.

## Acceptance Criteria
- [ ] \`backend/ocr/quality.py\` returns \`ImageQualityReport {score: 0-100, issues: []}\`
- [ ] Detected issues: \`low_resolution\`, \`excessive_glare\`, \`skewed_angle\`, \`partial_obstruction\`, \`blurry\`
- [ ] OpenCV pre-processing: deskew, denoise, contrast enhancement
- [ ] Quality score attached to every \`VerificationResult\`
- [ ] If score < 40, result flagged with \`low_confidence\` warning
- [ ] System does not reject images — degrades gracefully
- [ ] Unit tests: pristine (>80), simulated glare (40-70), very dark (<40)

## FedRAMP Controls
SI-10 (Information Input Validation)"

create_issue \
  "Implement Field Parser" \
  "Phase 2 — Core Intelligence" \
  "phase-2,backend,ai-ml,priority-critical" \
  "## Description
Raw OCR output must be parsed into the 6 structured fields required by TTB.

## Acceptance Criteria
- [ ] \`backend/ocr/parser.py\` maps raw OCR text to \`ExtractedFields\`
- [ ] Brand Name: extracted from first prominent text block
- [ ] Class/Type: via keyword proximity (VODKA, WHISKEY, ALE, etc.)
- [ ] ABV/Proof: regex for \`XX% Alc. by Vol.\` and \`XX Proof\`
- [ ] Net Contents: regex for XXXmL, XX fl oz, X L with unit normalization
- [ ] Name & Address: extracted from bottom-of-label text block
- [ ] Country of Origin: \`Product of X\` / \`Made in X\` patterns
- [ ] Government Warning: full verbatim block starting with GOVERNMENT WARNING
- [ ] Unit tests for each field with realistic OCR output examples

## FedRAMP Controls
SI-10 (Information Input Validation)"

create_issue \
  "Implement Fuzzy Matching Engine" \
  "Phase 2 — Core Intelligence" \
  "phase-2,backend,ai-ml,priority-critical" \
  "## Description
Compares extracted label fields against application data using per-field rules.

## Acceptance Criteria
- [ ] \`backend/matching/engine.py\` — \`compare(extracted, application_data) → MatchReport\`
- [ ] RapidFuzz \`token_sort_ratio\` for: Brand (≥90%), Class/Type (≥85%), Name & Address (≥80%), Country of Origin (≥90%)
- [ ] Numeric tolerance: ABV (±0.5%), Net Contents (±1% after unit normalization)
- [ ] Status per field: \`MATCH\` / \`PARTIAL_MATCH\` / \`NO_MATCH\`
- [ ] Overall status: \`MATCH\` / \`PARTIAL\` / \`FAIL\`
- [ ] Discrepancy detail: \`{extracted, expected, score}\` for each failed field
- [ ] Unit tests: exact match, minor variation, completely wrong values

## FedRAMP Controls
SI-10 (Information Input Validation)"

create_issue \
  "Implement Government Warning Exact Validator" \
  "Phase 2 — Core Intelligence" \
  "phase-2,backend,priority-critical" \
  "## Description
Government Warning is legally mandated verbatim text — exact word-for-word match required. No fuzzy tolerance.

## Acceptance Criteria
- [ ] \`backend/matching/exact_validator.py\` validates Government Warning independently
- [ ] Word-for-word comparison after whitespace normalization
- [ ] Verifies GOVERNMENT WARNING prefix is ALL-CAPS
- [ ] Returns: \`{valid, issues[], extracted_text, expected_text}\`
- [ ] Issue codes: \`WRONG_TEXT\`, \`MISSING_PREFIX\`, \`LOWERCASE_PREFIX\`, \`EXTRA_TEXT\`, \`MISSING_TEXT\`
- [ ] Any issue → field status \`NO_MATCH\` regardless of similarity score
- [ ] Unit tests: correct (valid), lowercase prefix (invalid), wrong text (invalid), extra words (invalid)

## FedRAMP Controls
SI-7 (Software, Firmware, and Information Integrity)"

create_issue \
  "Integrate SAST and Dependency Scanning" \
  "Phase 2 — Core Intelligence" \
  "phase-2,fedramp,fedramp-si,security,devops,priority-critical" \
  "## Description
FedRAMP SI-3 and SA-11 require automated code scanning in CI — not a manual step.

## Acceptance Criteria
- [ ] \`bandit\` (Python SAST) in CI; HIGH severity blocks merge
- [ ] \`pip-audit\` or \`safety\` in CI; known CVEs block merge
- [ ] \`eslint-plugin-security\` in frontend CI; HIGH findings block merge
- [ ] \`npm audit --audit-level=high\` in frontend CI
- [ ] \`trivy\` Docker image scan; CRITICAL CVEs block merge
- [ ] SAST results exported to GitHub Security tab (SARIF format)
- [ ] \`/docs/fedramp/SAST-RESULTS.md\` documents baseline findings and mitigations
- [ ] Suppressed findings have documented justification

## FedRAMP Controls
SI-3, SA-11, RA-5"

create_issue \
  "Implement Structured Audit Logging" \
  "Phase 2 — Core Intelligence" \
  "phase-2,fedramp,fedramp-au,backend,priority-critical" \
  "## Description
FedRAMP AU controls require all significant events logged for forensic reconstruction. No PII in logs.

## Acceptance Criteria
- [ ] Structured JSON logs via \`structlog\` for all API endpoints
- [ ] Each log: \`timestamp\`, \`request_id\`, \`endpoint\`, \`status_code\`, \`duration_ms\`, \`session_id\`, \`ocr_engine_used\`
- [ ] Must NOT appear in logs: \`image_bytes\`, \`base64_data\`, raw Name & Address
- [ ] Logged events: request received, OCR started/completed, match completed, errors, session expiry
- [ ] Log level configurable via \`LOG_LEVEL\` env var
- [ ] Logs written to stdout only (Docker best practice)
- [ ] Unit test: assert PII fields absent from log output

## FedRAMP Controls
AU-2 (Event Logging), AU-3 (Content of Audit Records), AU-9 (Protection of Audit Information)"

# ── EPIC 3 ──────────────────────────────────────────────────────────────────
create_issue \
  "EPIC 3 — Batch Processing & Review UI" \
  "Phase 3 — Batch & UI" \
  "epic,phase-3" \
  "## Goal
Reviewers can upload 200-300 labels at once, track progress in real time, and review results in a clean side-by-side interface.

### Child Issues
- [ ] Implement Batch Orchestrator
- [ ] Implement SSE Progress Streaming
- [ ] Build Single-Label Review UI
- [ ] Build Batch Upload & Progress UI
- [ ] Implement In-Memory Session Store & Export
- [ ] Implement Input Validation & Sanitization
- [ ] Implement Session Authentication"

create_issue \
  "Implement Batch Orchestrator" \
  "Phase 3 — Batch & UI" \
  "phase-3,backend,priority-critical" \
  "## Description
Parallel processing of 200-300 labels using Python asyncio. Must maintain ≤5s per label average.

## Acceptance Criteria
- [ ] \`backend/batch/orchestrator.py\` — \`start_batch(job_id, label_pairs[]) → AsyncIterator[Progress]\`
- [ ] \`asyncio.gather\` with configurable concurrency limit (default: 10 workers)
- [ ] Per-label progress events: \`{job_id, completed, total, latest: VerificationResult}\`
- [ ] Job state stored in-memory dict keyed by \`job_id\`
- [ ] Completed jobs retained for session; cleared on app restart
- [ ] Malformed images produce error result without aborting the batch
- [ ] Load test: 300 labels, ≤5s average, no worker crashes

## FedRAMP Controls
SI-12 (Information Management and Retention)"

create_issue \
  "Implement SSE Progress Streaming" \
  "Phase 3 — Batch & UI" \
  "phase-3,backend,frontend,priority-high" \
  "## Description
Server-Sent Events for real-time progress during 300-label batch processing.

## Acceptance Criteria
- [ ] \`GET /jobs/{job_id}/stream\` returns \`text/event-stream\`
- [ ] Events: \`progress\` (each label complete), \`complete\` (batch done), \`error\` (label failed)
- [ ] Frontend \`EventSource\` reconnects automatically if connection drops
- [ ] Progress bar updates: Processed N of 300 labels
- [ ] Most recent 5 results shown as live feed
- [ ] Stream closes cleanly when batch is complete

## FedRAMP Controls
SC-8 (Transmission Confidentiality)"

create_issue \
  "Build Single-Label Review UI" \
  "Phase 3 — Batch & UI" \
  "phase-3,frontend,priority-critical" \
  "## Description
Primary reviewer workflow. Must work for a 73-year-old non-technical user without training.

## Acceptance Criteria
- [ ] Large drag-and-drop upload zone with click-to-browse fallback
- [ ] Application data: labeled text fields for each of the 6 required fields (no free-text JSON)
- [ ] Results: two columns — Label Says vs Application Says — per field
- [ ] Status indicators: ✅ green (MATCH), ⚠️ yellow (PARTIAL), ❌ red (NO MATCH)
- [ ] Confidence score shown as percentage bar per field
- [ ] Government Warning displayed as its own section with exact-match indicator
- [ ] Image quality warning banner if score < 40
- [ ] Export CSV button at bottom of results
- [ ] No hidden menus or tooltips required
- [ ] Usability test: non-technical user completes verification in <2 minutes

## FedRAMP Controls
AC-3 (Access Enforcement)"

create_issue \
  "Build Batch Upload & Progress UI" \
  "Phase 3 — Batch & UI" \
  "phase-3,frontend,priority-critical" \
  "## Description
Bulk workflow for 200-300 labels with real-time progress tracking.

## Acceptance Criteria
- [ ] ZIP upload for images + CSV upload for application data
- [ ] CSV format validated client-side before submit
- [ ] Progress bar + counter after submit
- [ ] Live results feed: most recent 10 completed labels
- [ ] On completion: summary card — total MATCH / PARTIAL / FAIL counts
- [ ] Download Full Report button (Excel export)
- [ ] Restart button clears session without page reload

## FedRAMP Controls
SI-10 (Information Input Validation)"

create_issue \
  "Implement In-Memory Session Store & Export" \
  "Phase 3 — Batch & UI" \
  "phase-3,backend,priority-high" \
  "## Description
Results held in memory for session duration. No disk writes. Export to CSV/Excel for reviewer download.

## Acceptance Criteria
- [ ] \`backend/store/session_store.py\` — dict-backed store keyed by \`session_id\`
- [ ] Sessions expire after 4 hours of inactivity (configurable via env var)
- [ ] \`GET /jobs/{job_id}/export?format=csv\` returns RFC 4180-compliant CSV
- [ ] \`GET /jobs/{job_id}/export?format=xlsx\` returns Excel with color-coded status cells
- [ ] Export includes: label filename, each extracted field, each match status, confidence scores, overall status
- [ ] Memory usage capped: 300-label batch ~600KB
- [ ] Unit test: store → retrieve → export roundtrip

## FedRAMP Controls
SI-12 (Information Management and Retention), SC-28 (Protection of Information at Rest)"

create_issue \
  "Implement Input Validation & Sanitization" \
  "Phase 3 — Batch & UI" \
  "phase-3,fedramp,fedramp-si,backend,security,priority-critical" \
  "## Description
All inputs entering the API must be validated and sanitized. Bad inputs must never crash a worker.

## Acceptance Criteria
- [ ] Image uploads: validate MIME type server-side; reject non-image content
- [ ] Image size limit: 20MB per image; 500MB per batch ZIP
- [ ] CSV application data: validate required column headers; reject unknown columns
- [ ] All string fields: strip whitespace; max length enforced
- [ ] No \`eval()\`, \`exec()\`, \`subprocess\` with user-controlled input
- [ ] XSS prevented: all user data HTML-escaped in React
- [ ] Pydantic models enforce types on all API request bodies
- [ ] Fuzzing test: 20 malformed inputs; none crash the server

## FedRAMP Controls
SI-10, SI-16"

create_issue \
  "Implement Session Authentication" \
  "Phase 3 — Batch & UI" \
  "phase-3,fedramp,fedramp-ac,fedramp-ia,backend,frontend,priority-high" \
  "## Description
Results must not be accessible to unauthenticated users or other sessions.

## Acceptance Criteria
- [ ] On first visit, browser receives signed \`session_id\` cookie (HttpOnly, Secure, SameSite=Strict)
- [ ] All \`/jobs/*\` endpoints require session cookie; return 403 if absent or invalid
- [ ] Session IDs: \`secrets.token_urlsafe(32)\`
- [ ] Sessions expire server-side after 4 hours; cookie max-age matches
- [ ] Results for \`job_id\` accessible only to the session that created them
- [ ] No admin view that lists all sessions or jobs
- [ ] \`/docs/fedramp/SESSION-MANAGEMENT.md\` documents this control

## FedRAMP Controls
AC-3, IA-2, SC-23"

# ── EPIC 4 ──────────────────────────────────────────────────────────────────
create_issue \
  "EPIC 4 — Hardening & ATO Prep" \
  "Phase 4 — Hardening & ATO Prep" \
  "epic,phase-4" \
  "## Goal
Production-ready reliability, WCAG AA accessibility, and a complete FedRAMP documentation package ready for ISSO hand-off.

### Child Issues
- [ ] OpenCV Image Pre-Processing Pipeline
- [ ] Load Testing & Performance Validation
- [ ] Accessibility Audit & Remediation (WCAG AA)
- [ ] Comprehensive Error Handling & Graceful Degradation
- [ ] Complete FedRAMP Documentation Package
- [ ] Threat Model Documentation
- [ ] Final README & Deployment Guide"

create_issue \
  "OpenCV Image Pre-Processing Pipeline" \
  "Phase 4 — Hardening & ATO Prep" \
  "phase-4,backend,ai-ml,priority-high" \
  "## Description
Improve OCR accuracy on real-world label photos by pre-processing images before the OCR engine.

## Acceptance Criteria
- [ ] \`backend/ocr/preprocessor.py\`: deskew → denoise → sharpen → contrast
- [ ] OpenCV: \`getRotationMatrix2D\`, \`fastNlMeansDenoisingColored\`, \`equalizeHist\`
- [ ] Pre-processing adds ≤0.5s to total processing time
- [ ] Original image never modified — works on a copy
- [ ] A/B test: 20 real-world samples — quality score improvement documented
- [ ] Skipped if image quality score already > 80

## FedRAMP Controls
SI-10 (Information Input Validation)"

create_issue \
  "Load Testing & Performance Validation" \
  "Phase 4 — Hardening & ATO Prep" \
  "phase-4,testing,priority-critical" \
  "## Description
System must demonstrably meet ≤5s per label under realistic batch conditions. Results documented for FedRAMP package.

## Acceptance Criteria
- [ ] Locust or pytest-benchmark in \`/tests/load/\`
- [ ] Test: 300 labels submitted in batch; measure per-label latency
- [ ] P50 ≤ 5s, P95 ≤ 8s, P99 ≤ 12s — documented
- [ ] Zero worker crashes during 300-label run
- [ ] Memory below 2GB during batch (via \`psutil\`)
- [ ] Test runs against both OCR paths: cloud API and Tesseract fallback
- [ ] \`/docs/LOAD-TEST-RESULTS.md\` captures results, configuration, and environment

## FedRAMP Controls
AU-14, CP-10"

create_issue \
  "Accessibility Audit & Remediation (WCAG AA)" \
  "Phase 4 — Hardening & ATO Prep" \
  "phase-4,frontend,accessibility,priority-critical" \
  "## Description
Federal apps require Section 508 (WCAG 2.1 AA). UI must work for a 73-year-old non-technical user.

## Acceptance Criteria
- [ ] \`axe-core\` scan: zero WCAG AA violations on all 3 pages
- [ ] Keyboard navigation: all functionality reachable without mouse
- [ ] Tab order logical; focus indicator visible (min 3px outline)
- [ ] All images have descriptive \`alt\` text
- [ ] Color is never the only status indicator (icons + text alongside colors)
- [ ] Minimum font size 16px body, 14px secondary
- [ ] All form inputs have associated \`<label>\` elements
- [ ] Error messages announced via \`aria-live\` regions
- [ ] Tested with NVDA or VoiceOver
- [ ] \`/docs/ACCESSIBILITY-REPORT.md\` documents audit results

## FedRAMP Controls
PL-8 (Security and Privacy Architectures)"

create_issue \
  "Comprehensive Error Handling & Graceful Degradation" \
  "Phase 4 — Hardening & ATO Prep" \
  "phase-4,backend,frontend,priority-high" \
  "## Description
System must never show a blank screen, crash silently, or leave a reviewer without actionable information.

## Acceptance Criteria
- [ ] Backend: global FastAPI exception handler returns \`{error, message, request_id}\` — never raw stack traces
- [ ] OCR API timeout: returns result with \`ocr_engine: tesseract\` and adjusted confidence score
- [ ] Image completely unreadable: returns \`status: ERROR\` with helpful message
- [ ] Batch item failure: failed label gets error result; remaining labels continue
- [ ] Frontend: global React error boundary shows retry option
- [ ] Network error during SSE stream: UI shows Reconnecting... and auto-reconnects
- [ ] All error messages use plain language — no stack traces shown to users

## FedRAMP Controls
SI-17 (Fail-Safe Procedures), IR-8"

create_issue \
  "Complete FedRAMP Documentation Package" \
  "Phase 4 — Hardening & ATO Prep" \
  "phase-4,fedramp,documentation,priority-critical" \
  "## Description
Complete documentation package for hand-off to TTB ISSO to enable formal ATO pursuit.

## Acceptance Criteria
- [ ] \`/docs/fedramp/SSP-final.md\` — all control implementations documented
- [ ] \`/docs/fedramp/POAM.md\` — known gaps with remediation timeline
- [ ] \`/docs/fedramp/DATA-FLOW-final.md\` — finalized with actual endpoints and encryption posture
- [ ] \`/docs/fedramp/SAST-RESULTS.md\` — final scan results with all findings addressed
- [ ] \`/docs/fedramp/CONTROL-MATRIX.xlsx\` — NIST 800-53r5 Moderate baseline; each control marked
- [ ] \`/docs/fedramp/INCIDENT-RESPONSE-PLAN.md\` — procedures for OCR failures and incidents
- [ ] \`/docs/fedramp/SYSTEM-BOUNDARY.png\` — finalized from ADR-001
- [ ] Peer-reviewed by team member not involved in implementation

## FedRAMP Controls
PL-2, CA-5, CA-7"

create_issue \
  "Threat Model Documentation" \
  "Phase 4 — Hardening & ATO Prep" \
  "phase-4,fedramp,fedramp-ra,security,priority-high" \
  "## Description
FedRAMP RA controls require a documented threat model using STRIDE methodology.

## Acceptance Criteria
- [ ] \`/docs/fedramp/THREAT-MODEL.md\` using STRIDE framework
- [ ] Threats: Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation of Privilege
- [ ] Each threat: likelihood (L/M/H), impact (L/M/H), mitigating control, residual risk
- [ ] Top 3 risks identified with owner and mitigation timeline
- [ ] Data flow diagram annotated with trust boundaries
- [ ] Review sign-off by project lead

## FedRAMP Controls
RA-3 (Risk Assessment), RA-5 (Vulnerability Monitoring and Scanning)"

create_issue \
  "Final README & Deployment Guide" \
  "Phase 4 — Hardening & ATO Prep" \
  "phase-4,documentation,devops,priority-high" \
  "## Description
A system admin with no prior knowledge must be able to install and run the app using only the README.

## Acceptance Criteria
- [ ] \`README.md\`: prerequisites, one-command setup, env var reference, how to run tests
- [ ] \`/docs/DEPLOYMENT-GUIDE.md\`: network requirements (firewall rules), Docker install, air-gapped mode
- [ ] Firewall allowlist documented: outbound hostname for Claude Vision API with port and protocol
- [ ] Air-gapped mode: set \`OCR_MODE=local\` to force Tesseract; skip API key requirement
- [ ] Tested: team member not involved in dev follows guide and successfully runs app from scratch

## FedRAMP Controls
CM-6 (Configuration Settings), CM-7 (Least Functionality)"

echo ""
echo "🎉 Done! $REPO now has:"
echo "   - 26 labels"
echo "   - 4 milestones (Phases 1–4)"
echo "   - 32 issues (4 epics + 28 backlog tasks)"
echo ""
echo "Next steps:"
echo "  1. Go to github.com/$REPO/projects → New Project → Board or Roadmap"
echo "  2. Add all issues to the project"
echo "  3. Configure custom fields: Priority, Phase, FedRAMP Control"
echo "  4. Group Roadmap view by Milestone to see the 4-week plan"
