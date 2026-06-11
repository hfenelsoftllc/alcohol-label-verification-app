"""ISSUE 4.2 -- Load Testing & Performance Validation.

Drives the real FastAPI app **in-process** (via ``httpx.ASGITransport`` --
no separate server needed) through one 300-label batch:

    POST /verify/batch              (300 synthetic label PNGs + application_csv)
    GET  /jobs/{job_id}/stream       (SSE -- this is what actually runs the batch)

While the batch runs, this script:

* wraps ``batch.orchestrator._process_label`` to record the wall-clock time
  and ``VerificationResult`` of every one of the 300 labels (no production
  code changes -- same monkeypatch technique used by
  ``backend/tests/test_job_stream.py``);
* samples this process's RSS (plus any child processes, e.g. the
  ``tesseract`` binary) via ``psutil`` every 0.25s and tracks the peak.

It then reports P50/P95/P99 per-label latency, peak memory, and the count of
``ERROR`` results, against the ISSUE 4.2 acceptance criteria, and writes a
JSON results file alongside this script.

``OCR_MODE`` is read by ``ocr.adapter`` as a module-level constant at import
time, so this script must be invoked once per OCR path, with the env var set
*before* the interpreter starts:

    cd backend
    OCR_MODE=local python ../tests/load/load_test.py   # Tesseract fallback path
    OCR_MODE=auto  python ../tests/load/load_test.py   # Claude Vision path (real API calls)

See tests/load/README.md for prerequisites (tesseract-ocr binary,
ANTHROPIC_API_KEY) and the documented results in docs/LOAD-TEST-RESULTS.md.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import sys
import threading
import time
from pathlib import Path

import httpx
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.main import app  # noqa: E402
from app.models import OverallStatus  # noqa: E402
from batch import orchestrator  # noqa: E402
from ocr.adapter import OCR_MODE  # noqa: E402

import fixtures  # noqa: E402

#: Number of labels in the batch (ISSUE 4.2 AC: "300 labels submitted in batch").
LABEL_COUNT = int(os.getenv("LOAD_TEST_LABEL_COUNT", "300"))

#: Per-label latency budgets (ISSUE 4.2 AC).
P50_BUDGET_S = 5.0
P95_BUDGET_S = 8.0
P99_BUDGET_S = 12.0

#: Memory budget (ISSUE 4.2 AC).
MEMORY_BUDGET_MB = 2048.0

#: How often to sample RSS while the batch runs.
_MEMORY_SAMPLE_INTERVAL_S = 0.25

_RESULTS_DIR = Path(__file__).resolve().parent


def _percentile(data: list[float], pct: float) -> float:
    """Nearest-rank percentile: the smallest value at or above the `pct`th
    percentile of `data` (e.g. P99 of 300 samples is the 297th smallest)."""
    ordered = sorted(data)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


class _Instrumentation:
    """Wraps ``orchestrator._process_label`` to record per-label wall time
    and the resulting ``VerificationResult``, without touching production
    code. Restores the original function on exit."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.timings: list[float] = []
        self.results: list = []
        self._original = orchestrator._process_label

    def _wrapped(self, label):
        start = time.perf_counter()
        result = self._original(label)
        elapsed = time.perf_counter() - start
        with self._lock:
            self.timings.append(elapsed)
            self.results.append(result)
        return result

    def __enter__(self) -> "_Instrumentation":
        orchestrator._process_label = self._wrapped
        return self

    def __exit__(self, *exc_info: object) -> None:
        orchestrator._process_label = self._original


async def _sample_memory(stop: asyncio.Event, peak: list[float]) -> None:
    """Track the peak RSS (this process + any children, e.g. `tesseract`
    subprocesses) in MB, sampled every `_MEMORY_SAMPLE_INTERVAL_S`."""
    process = psutil.Process()
    while True:
        try:
            total = process.memory_info().rss
            for child in process.children(recursive=True):
                try:
                    total += child.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            total = 0
        peak[0] = max(peak[0], total / (1024 * 1024))

        if stop.is_set():
            return
        try:
            await asyncio.wait_for(stop.wait(), timeout=_MEMORY_SAMPLE_INTERVAL_S)
        except asyncio.TimeoutError:
            pass


async def _run() -> dict:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://testserver", timeout=httpx.Timeout(None)
    ) as client:
        # Mints the signed session cookie (ISSUE 3.7) required by /jobs/*.
        await client.get("/health")

        files = fixtures.build_batch_files(LABEL_COUNT)
        submit = await client.post("/verify/batch", files=files)
        submit.raise_for_status()
        body = submit.json()
        job_id = body["job_id"]
        assert body["total"] == LABEL_COUNT, body

        peak_memory = [psutil.Process().memory_info().rss / (1024 * 1024)]
        stop_event = asyncio.Event()
        sampler = asyncio.create_task(_sample_memory(stop_event, peak_memory))

        start = time.perf_counter()
        with _Instrumentation() as instrumentation:
            # Opening this stream is what drives start_batch() to completion
            # for a PENDING job (app/routers/jobs.py::_stream_progress).
            async with client.stream("GET", f"/jobs/{job_id}/stream") as response:
                response.raise_for_status()
                async for _ in response.aiter_bytes():
                    pass
        total_elapsed = time.perf_counter() - start

        stop_event.set()
        await sampler

    return {
        "ocr_mode": OCR_MODE,
        "label_count": LABEL_COUNT,
        "batch_max_workers": int(os.getenv("BATCH_MAX_WORKERS", str(orchestrator.DEFAULT_MAX_WORKERS))),
        "total_wall_time_s": total_elapsed,
        "timings_s": instrumentation.timings,
        "error_count": sum(1 for r in instrumentation.results if r.overall_status is OverallStatus.ERROR),
        "error_messages": [
            r.message for r in instrumentation.results if r.overall_status is OverallStatus.ERROR and r.message
        ],
        "peak_memory_mb": peak_memory[0],
    }


def _summarize(raw: dict) -> dict:
    timings = raw["timings_s"]
    summary = {k: v for k, v in raw.items() if k != "timings_s"}
    summary.update(
        labels_processed=len(timings),
        p50_s=_percentile(timings, 50),
        p95_s=_percentile(timings, 95),
        p99_s=_percentile(timings, 99),
        min_s=min(timings),
        max_s=max(timings),
        mean_s=statistics.mean(timings),
    )
    summary["zero_errors"] = raw["error_count"] == 0 and summary["labels_processed"] == raw["label_count"]
    summary["meets_latency_budget"] = (
        summary["p50_s"] <= P50_BUDGET_S and summary["p95_s"] <= P95_BUDGET_S and summary["p99_s"] <= P99_BUDGET_S
    )
    summary["meets_memory_budget"] = raw["peak_memory_mb"] <= MEMORY_BUDGET_MB
    return summary


def main() -> None:
    raw = asyncio.run(_run())
    summary = _summarize(raw)

    out_path = _RESULTS_DIR / f"results-{summary['ocr_mode']}.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"OCR mode:          {summary['ocr_mode']}")
    print(f"BATCH_MAX_WORKERS: {summary['batch_max_workers']}")
    print(f"Labels processed:  {summary['labels_processed']} / {summary['label_count']}")
    print(f"Total wall time:   {summary['total_wall_time_s']:.1f}s")
    print(
        f"P50 / P95 / P99:   {summary['p50_s']:.3f}s / {summary['p95_s']:.3f}s / {summary['p99_s']:.3f}s "
        f"(budgets <= {P50_BUDGET_S}s / {P95_BUDGET_S}s / {P99_BUDGET_S}s)"
    )
    print(f"Min / Max / Mean:  {summary['min_s']:.3f}s / {summary['max_s']:.3f}s / {summary['mean_s']:.3f}s")
    print(f"Peak memory:       {summary['peak_memory_mb']:.1f} MB (budget <= {MEMORY_BUDGET_MB} MB)")
    print(f"Errors:            {summary['error_count']}")
    print(f"Zero errors:           {summary['zero_errors']}")
    print(f"Meets latency budget:  {summary['meets_latency_budget']}")
    print(f"Meets memory budget:   {summary['meets_memory_budget']}")
    print(f"Wrote {out_path}")

    if not summary["zero_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
