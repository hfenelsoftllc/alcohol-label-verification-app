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

## Quick Start (one command)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and Docker
Compose v2.

```bash
git clone https://github.com/hfenelsoftllc/alcohol-label-verification-app.git
cd alcohol-label-verification-app
cp .env.example .env        # then edit .env (see Configuration below)
docker compose up
```

The app is available at **http://localhost:3000** (backend API at
**http://localhost:8000**, OpenAPI docs at **http://localhost:8000/docs**).

> The `docker-compose.yml`, Dockerfiles, and `.env.example` land in
> ISSUE 1.3 (Docker & Docker Compose Setup). Until then, see the per-service
> READMEs under [`backend/`](backend/) and [`frontend/`](frontend/) for running
> each service directly.

### Air-gapped / offline mode

Set `OCR_MODE=local` in `.env` to force the local Tesseract engine and skip the
Claude Vision API entirely (no API key required). See the deployment guide
(Phase 4) for firewall allowlist details.

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
└── docker-compose.yml
```

Each top-level directory has its own `README.md` describing its contents and the
issue that fleshes it out.

---

## Configuration

All configuration is via environment variables (no hardcoded config — CM-6).
The full reference ships with `.env.example` in ISSUE 1.3. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude Vision API key (omit in air-gapped mode) | — |
| `OCR_MODE` | `auto` (API + fallback) or `local` (Tesseract only) | `auto` |
| `VITE_API_URL` | Backend URL the frontend calls | `http://localhost:8000` |
| `LOG_LEVEL` | Structured log level | `INFO` |
| `SESSION_TTL_HOURS` | In-memory session expiry | `4` |

Secrets are **never** committed — `.env` is gitignored; only `.env.example`
(placeholder values) is tracked.

---

## Development

```bash
# Backend (FastAPI)
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend (Vite)
cd frontend && npm install && npm run dev
```

## Tests

```bash
cd backend && pytest          # backend unit tests
cd frontend && npm test       # frontend unit tests
# integration & load tests live in tests/
```

---

## Architecture

See [ADR-001 — System Architecture](docs/architecture/ADR-001-System-Architecture.md)
for the full decision record, technology stack, and data-flow diagrams.

**Stack:** React + Tailwind · FastAPI · Claude Vision (+ Tesseract fallback) ·
RapidFuzz matching · asyncio batch orchestration · Docker Compose.

## Project Management

Phased plan, epics, and issue backlog live in
[`project-management/PROJECT-PLAN.md`](project-management/PROJECT-PLAN.md).

## License

See [LICENSE](LICENSE).
