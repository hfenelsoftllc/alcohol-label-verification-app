# Load Test (ISSUE 4.2)

Validates the ≤5s/≤8s/≤12s (P50/P95/P99) per-label latency requirement and
the <2GB memory requirement under a realistic 300-label batch, against both
OCR paths. See [`docs/LOAD-TEST-RESULTS.md`](../../docs/LOAD-TEST-RESULTS.md)
for the documented results (FedRAMP AU-14/CP-10 evidence).

This is a **manual script**, not part of the CI gate (`pytest -q` runs with
`working-directory: backend`, so it never collects this directory) -- the
Claude Vision run below makes ~300 real API calls.

## What it does

[`load_test.py`](load_test.py) drives the FastAPI app **in-process** (no
server to start) via `httpx.ASGITransport`:

1. Generates 300 synthetic "label photo" PNGs (this repo has no real label
   photos -- same checkerboard generator family as
   [`backend/scripts/preprocessing_ab_test.py`](../../backend/scripts/preprocessing_ab_test.py))
   and a matching `application_csv`.
2. `POST /verify/batch`, then `GET /jobs/{job_id}/stream` (the SSE stream is
   what actually runs the batch).
3. Records the wall-clock time of every `_process_label` call (per-label
   latency) and the peak RSS of the process + any child processes (e.g.
   `tesseract`), sampled via `psutil`.
4. Prints a summary and writes `results-<OCR_MODE>.json`.

## Prerequisites

- `backend/requirements.txt`, `backend/requirements-dev.txt` (for `httpx`),
  and `tests/load/requirements.txt` (for `psutil`) installed.
- For `OCR_MODE=local` (Tesseract path): the `tesseract-ocr` binary on `PATH`
  (installed in `docker/backend.Dockerfile`, not on a bare Windows host).
- For `OCR_MODE=auto` (Claude Vision path): `ANTHROPIC_API_KEY` set in the
  environment. **This makes ~300 real API calls** (a few dollars, a couple
  of minutes at the default `BATCH_MAX_WORKERS=10`).

`OCR_MODE` is read by `ocr.adapter` at import time, so each path is a
**separate process invocation** -- it can't be toggled mid-run.

## Running

Run from the `backend/` directory so `import app`/`batch`/`ocr`/`matching`
resolve the same way they do for the app itself:

```sh
cd backend

# Tesseract fallback path (no external calls)
OCR_MODE=local python ../tests/load/load_test.py

# Claude Vision path (real API calls -- run once, see docs/LOAD-TEST-RESULTS.md)
OCR_MODE=auto python ../tests/load/load_test.py
```

### Via Docker (recommended on Windows, where `tesseract` isn't installed)

```sh
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd):/repo" -w /repo \
  -e ANTHROPIC_API_KEY \
  python:3.11-slim sh -c '
    apt-get update && apt-get install -y --no-install-recommends tesseract-ocr &&
    pip install -r backend/requirements.txt -r backend/requirements-dev.txt -r tests/load/requirements.txt &&
    cd backend &&
    OCR_MODE=local python ../tests/load/load_test.py &&
    OCR_MODE=auto  python ../tests/load/load_test.py
  '
```

## Output

- `results-local.json` / `results-auto.json` -- raw per-label timings and
  the summary (P50/P95/P99, peak memory, error count, pass/fail against the
  ISSUE 4.2 budgets). Not committed (see `.gitignore`).
- A non-zero exit code means at least one label came back with an `ERROR`
  result (a real crash/uncaught-exception signal) -- not merely a missed
  latency budget, since the Claude Vision path's latency depends on live API
  conditions outside this repo's control.
