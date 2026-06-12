# Deployment Guide (ISSUE 4.7)

**FedRAMP Control:** CM-6 (Configuration Settings), CM-7 (Least Functionality)

This guide covers installing Docker, the network/firewall requirements for a
single-host deployment, running in air-gapped mode, backup/restore, and how to
update a running instance. For the one-command quick start and the full
environment-variable reference, see the root [`README.md`](../README.md).

## Network Requirements (Firewall Rules)

The application is a single Docker Compose stack (`frontend` + `backend`
containers on an internal bridge network). The table below lists every network
flow that crosses the host boundary.

| Direction | Host / Port | Protocol | Purpose | Required? |
|---|---|---|---|---|
| **Outbound** | `api.anthropic.com` : **443** | **HTTPS (TLS 1.2+)** | Claude Vision API — primary OCR/vision extraction (`backend/ocr/adapter.py`, `anthropic` SDK) | **Optional.** Only used when `OCR_MODE=auto` (default) **and** `ANTHROPIC_API_KEY` is set. This is the **single outbound hostname** ALVA requires — see [Air-gapped / Offline Mode](#air-gapped--offline-mode) to disable it entirely. |
| **Inbound** | host : `FRONTEND_PORT` (default **3000**) | HTTP (TLS terminated by the hosting environment's ingress, if any) | Reviewer UI (frontend container, nginx) | Required — this is how reviewers reach the application. |
| **Inbound** (optional) | host : `BACKEND_PORT` (default **8000**) | HTTP | Direct backend API / OpenAPI docs (`/docs`) | Optional, for development and API exploration. The SPA itself only needs the frontend's `/api/*` reverse proxy (TB-1), so **do not publish this port externally in production** — restrict it to localhost/admin access (CM-7, least functionality). |
| **Internal** | `frontend` ↔ `backend` (Docker Compose bridge network, container ports 80/8000) | HTTP | nginx reverse-proxies `/api/*` to the backend (`docker/nginx/default.conf`) | Required; never leaves the Docker host. |

No other outbound connections are made by the application. The base container
images (`python:3.11-slim`, `node:20-alpine`, `nginx:stable-alpine`,
`redis:7-alpine`) are digest-pinned in the Dockerfiles (CM-2) and only need to
be pulled once at build time.

> Reviewer-facing HTTPS and TLS termination at the network ingress (e.g. a
> load balancer or reverse proxy in front of `FRONTEND_PORT`) are inherited
> from the hosting environment — see `docs/fedramp/SSP-final.md` §8 (AC-17,
> SC-8) and `docs/fedramp/DATA-FLOW-final.md` (trust boundary TB-0).

## Docker Installation

Install **Docker Engine 24+** and **Docker Compose v2** (the `docker compose`
subcommand, not the legacy standalone `docker-compose`):

- **Linux**: follow the [official install guide](https://docs.docker.com/engine/install/)
  for your distribution, which includes the `docker-compose-plugin` package.
- **Windows**: install [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
  with the WSL2 backend.
- **macOS**: install [Docker Desktop](https://docs.docker.com/desktop/install/mac-install/).

Verify the install:

```bash
docker --version
docker compose version
```

## Running the Application

```bash
git clone https://github.com/hfenelsoftllc/alcohol-label-verification-app.git
cd alcohol-label-verification-app
cp .env.example .env        # edit .env — see README.md "Configuration"
docker compose up -d        # -d runs detached; omit to follow logs in this terminal
```

Useful commands:

```bash
docker compose logs -f              # follow logs from both containers
docker compose ps                   # container status + health
curl http://localhost:8000/health   # backend readiness probe
docker compose down                 # stop and remove containers
```

The optional ephemeral Redis cache is started with:

```bash
docker compose --profile with-redis up -d
```

### Troubleshooting

- **`Error response from daemon: ports are not available` / `address already in use`**
  — another process on the host is already bound to `FRONTEND_PORT` (3000) or
  `BACKEND_PORT` (8000). Either stop that process, or set a different
  `FRONTEND_PORT`/`BACKEND_PORT` in `.env` and re-run `docker compose up -d`.

## Air-gapped / Offline Mode

Set in `.env`:

```ini
OCR_MODE=local
ANTHROPIC_API_KEY=
```

With `OCR_MODE=local`:

- The backend **never** attempts to reach `api.anthropic.com` — OCR is performed
  entirely by the local **Tesseract** engine, which is already bundled in
  `docker/backend.Dockerfile` (`tesseract-ocr` apt package). No additional
  installation is needed.
- `ANTHROPIC_API_KEY` is not read and can be left blank.
- The outbound firewall rule in the table above can be omitted entirely — the
  host needs **no internet access** to run the application once the images are
  built.

**Building images on an air-gapped host.** `docker compose build` itself
requires pulling the base images (`python:3.11-slim`, `node:20-alpine`,
`nginx:stable-alpine`) and, for the backend, the `tesseract-ocr` apt package.
If the deployment host has no internet access:

1. Build the images on a connected host (or CI), using the digest-pins already
   in `docker/backend.Dockerfile` and `docker/frontend.Dockerfile` to guarantee
   reproducibility (CM-2).
2. Export them with `docker save alvf-backend:latest alvf-frontend:latest -o alva-images.tar`.
3. Transfer the tarball to the air-gapped host and load it with `docker load -i alva-images.tar`.
4. Run `docker compose up -d` on the air-gapped host — Compose will use the
   already-loaded images instead of building.

**Verifying air-gapped operation.** Every verification result includes
`ocr_engine_used`. With `OCR_MODE=local`, every result (and the corresponding
`ocr_completed` audit log line on stdout — `AU-2`/`AU-3`) shows
`ocr_engine_used: "tesseract"`, confirming no calls to the Vision API were made.

> Even with `OCR_MODE=auto`, a blocked `api.anthropic.com` is **not** a failure:
> `extract_fields()` fails over to Tesseract immediately (no retries) and the
> batch/verification completes normally with `ocr_engine_used: "tesseract"` and
> a lower confidence score (see `docs/fedramp/THREAT-MODEL.md`, T-D3).

## Backup/Restore

**N/A — the application holds no persistent state to back up.** Per the
architecture decision (`docs/architecture/ADR-001-System-Architecture.md`) and
`SC-28`/`SI-12` in `docs/fedramp/SSP-final.md`:

- Label images, extracted fields, and match results live only in an in-memory
  job store (`backend/batch/store.py`) and are reaped after `SESSION_TTL_HOURS`
  (default 4h) or when the containers stop/restart.
- There is no database and no volume to snapshot.
- Reviewers must **export their results** (CSV/XLSX, via the UI) before closing
  a session or before an update/restart — exported files are the reviewer's
  responsibility to store per their own records-retention policy.
- "Restore" of the application itself is simply redeploying from source control
  (see [Updating the Application](#updating-the-application)) plus the site's
  `.env` file, which the operator should keep a copy of separately (it is
  gitignored and contains the optional `SESSION_SECRET_KEY` and
  `ANTHROPIC_API_KEY`).

## Updating the Application

```bash
git pull origin main             # or: git checkout <release-tag>
docker compose build              # rebuild images with the new code
docker compose up -d              # recreate containers with the new images
```

- **All active sessions are lost on restart** (in-memory store) — schedule
  updates for low-usage windows and ask reviewers to export results first.
- To roll back, `git checkout` the previous commit/tag and repeat the same two
  `docker compose` commands.
- After updating, confirm `docker compose ps` shows both containers healthy and
  `curl http://localhost:8000/health` returns `200`.

## Sizing Notes

The 300-label batch load test (`docs/LOAD-TEST-RESULTS.md`, ISSUE 4.2) stayed
under 2GB peak memory on both OCR paths with the default `BATCH_MAX_WORKERS=10`.
Lower `BATCH_MAX_WORKERS` on memory-constrained hosts, or raise it on hosts with
more CPU/RAM headroom — see the `.env.example` comment for this variable.

## Related Documents

- [`README.md`](../README.md) — quick start and full environment variable reference
- [`docs/fedramp/SSP-final.md`](fedramp/SSP-final.md) — system security plan (§4 boundary, §8 controls)
- [`docs/fedramp/DATA-FLOW-final.md`](fedramp/DATA-FLOW-final.md) — trust boundaries (TB-0..TB-3)
- [`docs/fedramp/THREAT-MODEL.md`](fedramp/THREAT-MODEL.md) — STRIDE threat model, including TB-3 (Claude Vision) risks
- [`docs/LOAD-TEST-RESULTS.md`](LOAD-TEST-RESULTS.md) — performance and memory sizing evidence
