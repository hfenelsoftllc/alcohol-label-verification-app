# SAST & Dependency Scanning — Baseline Results

**FedRAMP Controls:** SI-3 (Malicious Code Protection), SA-11 (Developer Security Testing),
RA-5 (Vulnerability Monitoring)
**Issue:** 2.6 — Integrate SAST and Dependency Scanning
**Baseline captured:** 2026-06-10

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
bandit -r backend -f sarif -o bandit.sarif --severity-level high --confidence-level high
```

**Baseline result:** 0 findings at any severity or confidence level.

```
Total lines of code: 1004
Total issues (by severity):  Undefined: 0  Low: 0  Medium: 0  High: 0
Total issues (by confidence): Undefined: 0  Low: 0  Medium: 0  High: 0
```

No `# nosec` suppressions exist in the codebase. If a finding is suppressed
in the future, the suppressing `# nosec B<id>` comment must include an
inline justification and is reviewed in the PR — see [`.bandit`](../../.bandit).

## Backend — pip-audit (SCA)

```
pip-audit -r backend/requirements.txt --strict
```

**Baseline result:** `No known vulnerabilities found` across all pinned
runtime dependencies (FastAPI, Pydantic, Anthropic SDK, OpenCV, RapidFuzz,
etc.).

## Frontend — eslint-plugin-security (JS/JSX SAST)

```
npm run lint   # eslint . , using frontend/eslint.config.js
```

`eslint.config.js` applies every rule from `eslint-plugin-security`'s
`recommended` config at `error` severity (covers `eval`, unsafe regex,
non-literal `require`/`fs` paths, child-process execution, pseudo-random
bytes, timing attacks, bidi-character injection, etc.), so any match fails
`npm run lint` and the CI job.

**Baseline result:** 0 findings across `frontend/src` and config files.
Verified the rule wiring is live by temporarily adding an `eval()` call,
which correctly failed lint with `security/detect-eval-with-expression`.

## Frontend — npm audit (SCA)

```
npm audit --audit-level=high
```

**Baseline result:** `found 0 vulnerabilities` (160 packages audited).

## Docker images — Trivy

```
trivy image --severity CRITICAL,HIGH --ignore-unfixed alvf-backend:ci
trivy image --severity CRITICAL,HIGH --ignore-unfixed alvf-frontend:ci
```

CI scans with `severity: CRITICAL` and `exit-code: 1` — only CRITICAL,
fixed CVEs fail the build. Both images currently have **0 CRITICAL**
findings, so the gate passes. For visibility, HIGH findings (informational,
do not block merge) are also captured below:

### `alvf-backend` (debian 13.5 base, `python:3.11-slim`)

| Library | CVE | Severity | Installed | Fixed in |
|---|---|---|---|---|
| libssl3t64 / openssl / openssl-provider-legacy | CVE-2026-45447 | HIGH | 3.5.6-1~deb13u1 | 3.5.6-1~deb13u2 |
| jaraco.context | CVE-2026-23949 | HIGH | 5.3.0 | 6.1.0 |
| wheel | CVE-2026-24049 | HIGH | 0.45.1 | 0.46.2 |

### `alvf-frontend` (alpine 3.23.4 base, `nginx:stable-alpine`)

| Library | CVE | Severity | Installed | Fixed in |
|---|---|---|---|---|
| libxml2 | CVE-2026-6732 | HIGH | 2.13.9-r0 | 2.13.9-r1 |

**Mitigation:** all four findings are in OS packages or pip's own bundled
build tooling (`jaraco.context`/`wheel`, pulled in transitively by `pip`
itself, not by `backend/requirements.txt`) inside the upstream base images —
not in application code or direct dependencies. None are CRITICAL, so they
do not block merge per the acceptance criteria. They will resolve on the
next periodic base-image digest bump (tracked as routine dependency
maintenance, not a `.trivyignore` suppression).

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
   bandit -r app ocr matching --severity-level high --confidence-level high && \
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
