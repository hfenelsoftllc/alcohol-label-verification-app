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
from dataclasses import dataclass

from app.models import (
    ApplicationData,
    BatchProgress,
    GovernmentWarningCheck,
    JobState,
    OcrEngine,
    OverallStatus,
    VerificationResult,
)
from app.stubs import new_session_id
from app.validation import validate_image_bytes
from batch import store
from matching import engine
from matching.exact_validator import validate_government_warning
from ocr.adapter import extract_fields
from ocr.quality import assess_image_quality

#: Default number of labels processed concurrently; override via BATCH_MAX_WORKERS.
DEFAULT_MAX_WORKERS = 10

#: Sentinel placed on the progress queue once every worker has finished.
_DONE = object()


@dataclass
class LabelInput:
    """One label image plus the application data to verify it against."""

    image_bytes: bytes
    application_data: ApplicationData
    filename: str | None = None


def _max_workers() -> int:
    return int(os.getenv("BATCH_MAX_WORKERS", str(DEFAULT_MAX_WORKERS)))


async def start_batch(job_id: str, label_pairs: Iterable[LabelInput]) -> AsyncIterator[BatchProgress]:
    """Process `label_pairs` concurrently, yielding progress as each finishes.

    Updates the `Job` in `batch.store`: `state` moves PENDING -> PROCESSING
    -> COMPLETED, `completed` increments per finished label, and `results`
    is populated in input order once the batch finishes.
    """
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"job '{job_id}' not found")

    labels = list(label_pairs)
    job.state = JobState.PROCESSING

    results: list[VerificationResult | None] = [None] * len(labels)
    semaphore = asyncio.Semaphore(_max_workers())
    queue: asyncio.Queue = asyncio.Queue()

    async def _worker(index: int, label: LabelInput) -> None:
        async with semaphore:
            result = await asyncio.to_thread(_process_label, label)
        results[index] = result
        job.completed += 1
        await queue.put(BatchProgress(job_id=job_id, completed=job.completed, total=job.total, latest=result))

    async def _run_all() -> None:
        try:
            await asyncio.gather(*(_worker(i, label) for i, label in enumerate(labels)))
        finally:
            job.results = [r for r in results if r is not None]
            job.state = JobState.COMPLETED
            await queue.put(_DONE)

    runner = asyncio.create_task(_run_all())

    while True:
        item = await queue.get()
        if item is _DONE:
            break
        yield item

    await runner


def _process_label(label: LabelInput) -> VerificationResult:
    """Run one label through OCR, matching, and Government Warning checks.

    Any failure (e.g. an undecodable image) is reported as an ERROR result
    for this label rather than raised, so it cannot abort the whole batch
    (FedRAMP SI-10).
    """
    try:
        validate_image_bytes(label.image_bytes)
        image_quality = assess_image_quality(label.image_bytes)
        extracted = extract_fields(label.image_bytes)
    except Exception as exc:
        return _error_result(label, str(exc))

    match_report = engine.compare(extracted, label.application_data)
    warning_check = validate_government_warning(
        extracted.government_warning, label.application_data.government_warning
    )

    overall_status = match_report.overall_status
    if not warning_check.valid:
        overall_status = OverallStatus.FAIL

    return VerificationResult(
        session_id=new_session_id(),
        overall_status=overall_status,
        fields=match_report.fields,
        government_warning=warning_check,
        image_quality_score=image_quality.score,
        quality_issues=image_quality.issues,
        confidence_score=extracted.confidence_score,
        ocr_engine_used=extracted.ocr_engine_used,
        filename=label.filename,
    )


def _error_result(label: LabelInput, message: str) -> VerificationResult:
    return VerificationResult(
        session_id=new_session_id(),
        overall_status=OverallStatus.ERROR,
        fields=[],
        government_warning=GovernmentWarningCheck(valid=False, issues=["PROCESSING_ERROR"]),
        image_quality_score=0.0,
        quality_issues=[],
        confidence_score=0.0,
        # No OCR engine ran; TESSERACT is the offline default and the closest
        # available value to "none" without adding a new enum member.
        ocr_engine_used=OcrEngine.TESSERACT,
        filename=label.filename,
        message=message,
    )
