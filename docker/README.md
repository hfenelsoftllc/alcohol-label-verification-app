# Docker — Container Build & Orchestration

Dockerfiles and supporting assets for building the backend and frontend images.
The root `docker-compose.yml` orchestrates the full stack with a single command.

## Planned contents

```
docker/
├── backend.Dockerfile    # Python 3.11-slim, pinned deps, non-root user
├── frontend.Dockerfile   # Node 20-alpine multi-stage build, nginx static serve
└── nginx/                # nginx config for serving the built frontend
```

All base images are digest-pinned (e.g. `python:3.11-slim@sha256:...`) to satisfy
CM-2 (Baseline Configuration).

> Image and compose setup lands in ISSUE 1.3 (Docker & Docker Compose Setup).
