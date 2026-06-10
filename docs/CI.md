# Continuous Integration

The CI pipeline ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) is the
enforcement gate for code quality and security. It runs on every pull request and
on every push to `main`. The aggregate **CI Success** check is a required status
check in branch protection — nothing merges to `main` until it passes.

## Jobs

| Job | Checks | Blocks merge on |
|-----|--------|-----------------|
| **Backend** | `pytest`, `bandit` (SAST → SARIF), `pip-audit` (SCA) | test failure, HIGH-severity bandit finding, known CVE |
| **Frontend** | `eslint` (with `eslint-plugin-security`), `npm audit` | lint error, HIGH-severity advisory |
| **Docker** | `docker build`, `trivy` image scan (SARIF) | build failure, **CRITICAL** CVE |
| **CI Success** | Aggregates the three jobs above | any upstream job not succeeding |

SAST/scan results are uploaded to the **GitHub Security tab** in SARIF format
(Bandit and Trivy). To suppress a Trivy finding, add a justified entry to
[`.trivyignore`](../.trivyignore).

### Bootstrap behavior

The backend, frontend, and docker jobs detect whether their part of the monorepo
has been scaffolded and **skip gracefully** if not. The pipeline is therefore
green during Phase 1 bootstrap and activates automatically as the backend
(ISSUE 1.4), frontend (ISSUE 1.5), and Docker images (ISSUE 1.3) land — no
workflow edits required.

## Secrets

`ANTHROPIC_API_KEY` is the only secret CI consumes. It is:

- **Injected from GitHub Secrets only** — never hardcoded, never committed.
  Add it under *Settings → Secrets and variables → Actions* as a repository
  secret named `ANTHROPIC_API_KEY`.
- Exposed to a **single step** (backend `pytest`) as an environment variable and
  **never logged**. The pipeline uses no `set -x` / command tracing, so the value
  cannot leak into job logs. GitHub additionally masks registered secrets in logs.

Tests must **mock** the Claude Vision API rather than make live calls, so a valid
key is not required for CI to pass.

## Action pinning

Third-party actions are pinned to release tags. Hardening to full commit-SHA pins
is tracked under ISSUE 2.6 (Integrate SAST and Dependency Scanning).
