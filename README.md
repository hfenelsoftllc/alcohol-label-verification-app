# Alcohol Label Verification PoC

AI-powered verification of alcohol beverage labels against their COLA application
data, built for the TTB (Alcohol and Tobacco Tax and Trade Bureau). The system
extracts the required fields from a label image with OCR/vision, then matches
them against the submitted application — fuzzy matching for most fields, strict
word-for-word matching for the Government Warning.

Designed to run in a **firewalled government environment**: it tries a whitelisted
Claude Vision endpoint first and falls back to local Tesseract when the network is
blocked. No database, no persistent storage — label images and extracted data are
processed **ephemerally, in memory only**.

> **Classification:** FedRAMP Moderate (PoC documentation package — full ATO out
> of scope). See [`docs/fedramp/`](docs/fedramp/).

---

## Prerequisites

- **[Docker Engine](https://docs.docker.com/get-docker/)** 24+ and **Docker
  Compose v2** (`docker compose version` — bundled with Docker Desktop and the
  `docker-compose-plugin` package on Linux).
- **git**, to clone the repository.
- A modern browser (Chrome, Edge, Firefox, Safari) to use the reviewer UI.
- Network access to `api.anthropic.com` on port 443 if you want the higher-accuracy
  Claude Vision OCR path — otherwise see [Air-gapped / offline mode](#air-gapped--offline-mode)
  below. No other outbound access is required.

---

## Quick Start (one command)

```bash
git clone https://github.com/hfenelsoftllc/alcohol-label-verification-app.git
cd alcohol-label-verification-app
cp .env.example .env        # then edit .env (see Configuration below)
docker compose up
```

The first run builds the backend and frontend images (a couple of minutes);
subsequent runs reuse the cached layers.

### Accessing the app

| What | URL |
|------|-----|
| Reviewer UI (frontend) | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| OpenAPI / Swagger docs | http://localhost:8000/docs |
| Backend health check | http://localhost:8000/health |

The UI has three views: upload a single label (`/`), review its match results
(`/results/:sessionId`), and upload a batch of labels with live progress (`/batch`).

To stop the stack, press `Ctrl+C`, or run `docker compose down` from another
terminal. All state is in-memory, so stopping the containers clears every
session — there is nothing to back up (see the
[deployment guide](docs/DEPLOYMENT-GUIDE.md#backuprestore)).

### Air-gapped / offline mode

Set `OCR_MODE=local` in `.env` to force the local Tesseract engine and skip the
Claude Vision API entirely — `ANTHROPIC_API_KEY` can be left blank. See
[`docs/DEPLOYMENT-GUIDE.md`](docs/DEPLOYMENT-GUIDE.md#air-gapped--offline-mode)
for the full firewall allowlist and air-gapped setup.

---

## Repository Structure

```
.
├── frontend/    # React 18 + Vite + Tailwind SPA (reviewer UI)
├── backend/     # Python FastAPI service (OCR, matching, batch, export)
├── docker/      # Dockerfiles + nginx config
├── docs/        # Architecture (ADR-001), FedRAMP package, guides
├── tests/       # Integration & load tests
├── .github/     # CODEOWNERS + CI workflows
├── docker-compose.yml
├── vercel.json       # Vercel "Services" config (frontend + backend as one project)
└── .vercelignore     # Files excluded from the Vercel deployment bundle
```

Each top-level directory has its own `README.md` describing its contents.

---

## Configuration

All configuration is via environment variables (no hardcoded config — CM-6).
Copy [`.env.example`](.env.example) to `.env` and adjust as needed; `.env` is
gitignored and never committed.

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude Vision API key. Required unless `OCR_MODE=local`. | _(empty)_ |
| `OCR_MODE` | `auto` (Claude Vision, falling back to Tesseract) or `local` (Tesseract only, air-gapped) | `auto` |
| `CLAUDE_VISION_MODEL` | Claude model used for vision extraction | `claude-opus-4-8` |
| `OCR_API_TIMEOUT_SECONDS` | Seconds to wait on the Vision API before failing over to Tesseract (no retries) | `30` |
| `OCR_CLAUDE_CONFIDENCE` | Confidence score (0-100) recorded for Claude Vision results | `95` |
| `OCR_TESSERACT_CONFIDENCE` | Confidence score (0-100) recorded for local Tesseract results | `60` |
| `LOG_LEVEL` | Structured log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `SESSION_TTL_HOURS` | In-memory session/job expiry, in hours; also the session cookie's `Max-Age` | `4` |
| `SESSION_SECRET_KEY` | HMAC key for signing session cookies. Leave blank for a single instance; set explicitly (e.g. `openssl rand -hex 32`) when running multiple backend instances behind a load balancer | random per-process |
| `MAX_IMAGE_MB` | Maximum size of a single uploaded label image, in MB | `20` |
| `MAX_BATCH_MB` | Maximum cumulative image size for one `/verify/batch` request, in MB. On Vercel, lower this (e.g. `4`) to stay under the platform's request body size limit | `500` |
| `BATCH_MAX_WORKERS` | Labels processed concurrently within a single batch job | `10` |
| `REDIS_URL` | Optional Redis URL (`redis://redis:6379/0` with `--profile with-redis`) for cross-invocation session/job storage. Blank uses the in-process dict store — fine for Docker/local (one long-lived instance), but **required on Vercel** (`rediss://...` from the Upstash Marketplace integration), where each request may hit a different serverless instance | _(empty)_ |
| `VITE_API_URL` | Base URL the frontend SPA calls, baked in at build time. Default `/api` is reverse-proxied to the backend by nginx (same-origin, no CORS) | `/api` |
| `FRONTEND_PORT` | Host port mapped to the frontend container | `3000` |
| `BACKEND_PORT` | Host port mapped to the backend container | `8000` |

---

## Development

To run the services directly (without Docker) for local development:

```bash
# Backend (FastAPI)
cd backend && python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend (Vite)
cd frontend && npm install && npm run dev
```

## Tests

```bash
# Backend: unit tests, SAST, and dependency audit
cd backend
pytest -q
bandit -r . -x ./.venv
pip-audit

# Frontend: lint, unit tests, and dependency audit
cd frontend
npm run lint
npm test
npm audit
```

Integration and load tests live in [`tests/`](tests/) — see
[`tests/README.md`](tests/README.md) and
[`tests/load/README.md`](tests/load/README.md) (the 300-label batch performance
test is a manual script, not part of the CI gate).

The full CI pipeline — which runs all of the above on every PR — is documented in
[`docs/CI.md`](docs/CI.md).

---

## Architecture

See [ADR-001 — System Architecture](docs/architecture/ADR-001-System-Architecture.md)
for the full decision record, technology stack, and data-flow diagrams.

**Stack:** React + Tailwind · FastAPI · Claude Vision (+ Tesseract fallback) ·
RapidFuzz matching · asyncio batch orchestration · Docker Compose.

## Deployment

For production-style deployments — network/firewall requirements, Docker
installation, air-gapped operation, and how to update a running instance — see
[`docs/DEPLOYMENT-GUIDE.md`](docs/DEPLOYMENT-GUIDE.md).

### Vercel (hosted demo)

A hosted demo also runs on [Vercel](https://vercel.com), as a single project
using [Vercel "Services"](https://vercel.com/docs/multi-tenant/services) to
deploy the Vite frontend and the FastAPI backend together under one domain:

**Live demo:** <https://alcohol-label-verification-app-ivory.vercel.app/>

How it's wired up:

- [`vercel.json`](vercel.json) declares two services: `frontend` (Vite,
  routed at `/`) and `backend` (FastAPI, routed at `/api`). Vercel strips the
  `/api` prefix before invoking the backend function, so
  `backend/app/main.py`'s routes (`/health`, `/verify`, `/jobs/...`) stay
  unprefixed — the same as behind nginx in Docker Compose.
- Each request can land on a different serverless instance, so the session
  and batch-job stores (`backend/app/session.py`, `backend/batch/store.py`)
  are backed by Redis whenever `REDIS_URL` is set. With `REDIS_URL` unset
  (Docker/local/tests), they fall back to the original in-process dict
  stores, unchanged.
- [`.vercelignore`](.vercelignore) excludes dev/test files (`backend/.venv`,
  `backend/tests`, `frontend/node_modules`, etc.) from the deployment bundle.

To deploy your own copy:

1. [Install the Vercel CLI](https://vercel.com/docs/cli) and run `vercel link`
   from the repo root.
2. In the Vercel dashboard, set the project's **Framework Preset** to
   **Services** — required for `experimentalServices` in `vercel.json` to
   take effect.
3. Add the **Upstash Redis** integration from the Vercel Marketplace and copy
   its `rediss://...` connection string.
4. Set project environment variables (`vercel env add <NAME> <environment>`):
   `REDIS_URL` (from step 3), `ANTHROPIC_API_KEY`, `SESSION_SECRET_KEY`
   (`openssl rand -hex 32`), `OCR_MODE=auto`, and `MAX_BATCH_MB=4`.
5. `vercel deploy --prod` (omit `--prod` for a preview deployment).

Smoke-test with `GET /api/health` — it should return
`{"status":"ok","version":"..."}`.

## FedRAMP Documentation

The FedRAMP Moderate documentation package (System Security Plan, data flow,
threat model, POA&M, control matrix, and more) lives in
[`docs/fedramp/`](docs/fedramp/).

## Project Management

Phased plan, epics, and issue backlog live in
[`project-management/PROJECT-PLAN.md`](project-management/PROJECT-PLAN.md).

## License

See [LICENSE](LICENSE).
