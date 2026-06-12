# SAST & Dependency Scanning Results

| | |
|---|---|
| **System Name** | Alcohol Label Verification App (ALVA) — TTB COLA Automation PoC |
| **Document Status** | **FINAL** — Phase 4 (ISSUE 4.5, complete FedRAMP documentation package) |
| **FedRAMP Controls** | SI-3 (Malicious Code Protection), SA-11 (Developer Security Testing), RA-5 (Vulnerability Monitoring) |
| **Baseline captured** | 2026-06-10 (ISSUE 2.6) |
| **Final scan re-run** | 2026-06-11 (ISSUE 4.5) |

> **Scope note.** This document records the results of re-running every scanner in
> [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) against the codebase as of
> ISSUE 4.5, for hand-off to the TTB ISSO. All findings below are either **clean** or
> **mitigated** (tracked as routine base-image maintenance, not application-code defects) — see
> [`POAM.md`](./POAM.md), which does not carry any SAST/SCA/Trivy item as an open gap.

All scanners below run automatically on every PR and push to `main` via
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml). The aggregate
`CI Success` check is the single required status check on `main` — a PR
cannot merge unless every scanner below passes.

| Scanner | Target | Blocks merge on | CI job |
|---|---|---|---|
| Bandit | `backend/` (Python SAST) | HIGH severity + HIGH confidence | `Backend (pytest, bandit, pip-audit)` |
| pip-audit | `backend/requirements.txt` (SCA) | Any known CVE (`--strict`) | `Backend (pytest, bandit, pip-audit)` |
| eslint-plugin-security | `frontend/` (JS/JSX SAST) | Any finding (configured as `error`) | `Frontend (eslint-security, npm audit)` |
| npm audit | `frontend/package-lock.json` (SCA) | HIGH or CRITICAL CVE (`--audit-level=high`) | `Frontend (eslint-security, npm audit)` |
| Trivy | `alvf-backend` / `alvf-frontend` images | CRITICAL CVE (fixed, not in `.trivyignore`) | `Docker (build + trivy)` |

Bandit and Trivy results are also exported as SARIF and uploaded to the
repository's **Security → Code scanning** tab (`security-events: write`
permission, `github/codeql-action/upload-sarif`).

---

## Backend — Bandit (Python SAST)

```
bandit -r app ocr matching batch --severity-level high --confidence-level high
```

**Final result (2026-06-11):** 0 findings at any severity or confidence
level — unchanged from baseline.

```
Total lines of code: 1790
Total lines skipped (#nosec): 0
Total issues (by severity):  Undefined: 0  Low: 0  Medium: 0  High: 0
Total issues (by confidence): Undefined: 0  Low: 0  Medium: 0  High: 0
```

The codebase has grown from 1004 to 1790 lines of code since the Phase 2
baseline (Phases 3–4: batch processing, session auth, preprocessing,
pipeline consolidation), with no new findings.

No `# nosec` suppressions exist in the codebase. If a finding is suppressed
in the future, the suppressing `# nosec B<id>` comment must include an
inline justification and is reviewed in the PR — see [`.bandit`](../../.bandit).

**Note on scope:** the command above scans the application-code packages
(`app`, `ocr`, `matching`, `batch` — 1790 LOC) for a focused, reviewable
result. CI's required gate
([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)) runs
`bandit -r backend -f sarif -o bandit.sarif --severity-level high --confidence-level high`,
which additionally covers `backend/tests/` and `backend/scripts/` (~3,694 LOC
total as of this release). Both scopes report **0 findings** at HIGH
severity/confidence.

## Backend — pip-audit (SCA)

```
pip-audit -r backend/requirements.txt --strict
```

**Final result (2026-06-11):** `No known vulnerabilities found` across all
pinned runtime dependencies (FastAPI, Pydantic, Anthropic SDK, OpenCV,
RapidFuzz, openpyxl, etc.) — unchanged from baseline.

## Frontend — eslint-plugin-security (JS/JSX SAST)

```
npm run lint   # eslint . , using frontend/eslint.config.js
```

`eslint.config.js` applies every rule from `eslint-plugin-security`'s
`recommended` config at `error` severity (covers `eval`, unsafe regex,
non-literal `require`/`fs` paths, child-process execution, pseudo-random
bytes, timing attacks, bidi-character injection, etc.), so any match fails
`npm run lint` and the CI job.

**Final result (2026-06-11):** 0 findings across `frontend/src` and config
files — unchanged from baseline. Baseline verification confirmed the rule
wiring is live by temporarily adding an `eval()` call, which correctly
failed lint with `security/detect-eval-with-expression`.

## Frontend — npm audit (SCA)

```
npm audit --audit-level=high
```

**Final result (2026-06-11):** `found 0 vulnerabilities` — unchanged from
baseline.

## Docker images — Trivy

```
trivy image --severity CRITICAL,HIGH --ignore-unfixed alvf-backend:ci
trivy image --severity CRITICAL,HIGH --ignore-unfixed alvf-frontend:ci
```

CI scans with `severity: CRITICAL` and `exit-code: 1` — only CRITICAL,
fixed CVEs fail the build. Both images currently have **0 CRITICAL**
findings, so the gate passes. For visibility, HIGH findings (informational,
do not block merge) are also captured below — **re-run on 2026-06-11**
against the final images built from `docker/backend.Dockerfile` and
`docker/frontend.Dockerfile`:

### `alvf-backend` (debian 13.5 base, `python:3.11-slim`)

Total: 3 (HIGH: 3, CRITICAL: 0) — unchanged from baseline.

| Library | CVE | Severity | Installed | Fixed in |
|---|---|---|---|---|
| libssl3t64 / openssl / openssl-provider-legacy | CVE-2026-45447 | HIGH | 3.5.6-1~deb13u1 | 3.5.6-1~deb13u2 |
| jaraco.context | CVE-2026-23949 | HIGH | 5.3.0 | 6.1.0 |
| wheel | CVE-2026-24049 | HIGH | 0.45.1 | 0.46.2 |

### `alvf-frontend` (alpine 3.23.4 base, `nginx:stable-alpine`)

Total: 3 (HIGH: 3, CRITICAL: 0) — **two new findings since baseline**
(`libcrypto3` and `libssl3`, both CVE-2026-45447) from an upstream alpine
base-image OpenSSL update; `libxml2` is unchanged.

| Library | CVE | Severity | Installed | Fixed in |
|---|---|---|---|---|
| libcrypto3 | CVE-2026-45447 | HIGH | 3.5.6-r0 | 3.5.7-r0 |
| libssl3 | CVE-2026-45447 | HIGH | 3.5.6-r0 | 3.5.7-r0 |
| libxml2 | CVE-2026-6732 | HIGH | 2.13.9-r0 | 2.13.9-r1 |

**Mitigation:** all findings are in OS packages or pip's own bundled build
tooling (`jaraco.context`/`wheel`, pulled in transitively by `pip` itself,
not by `backend/requirements.txt`) inside the upstream base images — not in
application code or direct dependencies. The two new `alvf-frontend`
findings (`libcrypto3`/`libssl3`, CVE-2026-45447) are the **same upstream
OpenSSL advisory** already tracked for `alvf-backend`, now also present in
the `nginx:stable-alpine` base.
None are CRITICAL, so they do not block merge per the acceptance criteria
and none are tracked in [`POAM.md`](./POAM.md) as an open gap. They will
resolve on the next periodic base-image digest bump (tracked as routine
dependency maintenance, not a `.trivyignore` suppression).

## Suppression policy

- **Trivy:** [`.trivyignore`](../../.trivyignore) — currently empty. Any
  CVE suppression must include the CVE ID, a justification, owner, and a
  review-by date.
- **Bandit:** [`.bandit`](../../.bandit) — currently no skips. Any
  suppression must be an inline `# nosec B<id> -- justification` comment,
  reviewed in the PR that adds it.

## Reproducing locally

```powershell
# Backend: bandit + pip-audit
docker run --rm -v "${PWD}\backend:/app" -w /app python:3.11-slim sh -c `
  "pip install -q -r requirements-dev.txt 'bandit[sarif]' pip-audit && \
   bandit -r app ocr matching batch --severity-level high --confidence-level high && \
   pip-audit -r requirements.txt"

# Frontend: eslint-plugin-security + npm audit
docker run --rm -v "${PWD}\frontend:/app" -w /app node:20-slim sh -c `
  "npm install && npm run lint && npm audit --audit-level=high"

# Docker images: Trivy
docker build -t alvf-backend:ci -f docker/backend.Dockerfile .
docker build -t alvf-frontend:ci -f docker/frontend.Dockerfile .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest `
  image --severity CRITICAL,HIGH --ignore-unfixed alvf-backend:ci
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest `
  image --severity CRITICAL,HIGH --ignore-unfixed alvf-frontend:ci
```
