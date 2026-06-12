"""Batch orchestrator (ISSUE 3.1).

`start_batch` runs a batch of labels through the OCR -> matching ->
Government Warning pipeline with bounded concurrency (`asyncio.gather` over
a `asyncio.Semaphore`-limited set of workers, each running the synchronous
pipeline via `asyncio.to_thread`). It updates the `Job` record in
`batch.store` in place and yields a `BatchProgress` event as each label
finishes, so callers can stream progress (ISSUE 3.2).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterable

from app.models import BatchProgress, GovernmentWarningCheck, JobState, OcrEngine, OverallStatus, VerificationResult
from app.pipeline import INVALID_IMAGE_MESSAGE, new_session_id, run_verification
from app.validation import validate_image_bytes
from batch import store
from batch.store import LabelInput

#: Default number of labels processed concurrently; override via BATCH_MAX_WORKERS.
DEFAULT_MAX_WORKERS = 10

#: Sentinel placed on the progress queue once every worker has finished.
_DONE = object()

__all__ = ["DEFAULT_MAX_WORKERS", "LabelInput", "start_batch"]


def _max_workers() -> int:
    return int(os.getenv("BATCH_MAX_WORKERS", str(DEFAULT_MAX_WORKERS)))


async def start_batch(job_id: str, label_pairs: Iterable[LabelInput]) -> AsyncIterator[BatchProgress]:
    """Process `label_pairs` concurrently, yielding progress as each finishes.

    Updates the `Job` in `batch.store`: `state` moves PENDING -> PROCESSING
    -> COMPLETED, `completed` increments per finished label, and `results[i]`
    is filled in (replacing its `None` placeholder) as soon as label `i`
    finishes — so an SSE stream (ISSUE 3.2) can report partial progress to a
    reconnecting client without waiting for the whole batch.
    """
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"job '{job_id}' not found")

    labels = list(label_pairs)
    job.state = JobState.PROCESSING
    job.results = [None] * len(labels)
    store.save_job(job)

    semaphore = asyncio.Semaphore(_max_workers())
    queue: asyncio.Queue = asyncio.Queue()

    async def _worker(index: int, label: LabelInput) -> None:
        async with semaphore:
            result = await asyncio.to_thread(_process_label, label)
        job.results[index] = result
        job.completed += 1
        store.save_job(job)
        await queue.put(BatchProgress(job_id=job_id, completed=job.completed, total=job.total, latest=result))

    async def _run_all() -> None:
        try:
            await asyncio.gather(*(_worker(i, label) for i, label in enumerate(labels)))
        finally:
            job.state = JobState.COMPLETED
            store.save_job(job)
            await queue.put(_DONE)

    runner = asyncio.create_task(_run_all())

    while True:
        item = await queue.get()
        if item is _DONE:
            break
        yield item

    await runner


def _process_label(label: LabelInput) -> VerificationResult:
    """Run one label through the verification pipeline.

    Callers already run `validate_image_bytes` on every image at batch
    submission time; this check is defense-in-depth. Any failure here, or
    anywhere in `run_verification`, is reported as an ERROR result for this
    label rather than raised, so it cannot abort the whole batch (FedRAMP
    SI-10, SI-17).
    """
    try:
        validate_image_bytes(label.image_bytes)
    except Exception:
        return VerificationResult(
            session_id=new_session_id(),
            overall_status=OverallStatus.ERROR,
            fields=[],
            government_warning=GovernmentWarningCheck(valid=False, issues=["INVALID_IMAGE"]),
            image_quality_score=0.0,
            quality_issues=[],
            confidence_score=0.0,
            ocr_engine_used=OcrEngine.TESSERACT,
            filename=label.filename,
            message=INVALID_IMAGE_MESSAGE,
        )

    return run_verification(label.image_bytes, label.application_data, filename=label.filename)
