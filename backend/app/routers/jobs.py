"""Batch job status, results, export, and progress-stream endpoints."""

from __future__ import annotations

import asyncio
import csv
import io
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.models import (
    LABEL_FIELD_NAMES,
    BatchProgress,
    BatchSummary,
    JobResultsResponse,
    JobState,
    JobStatusResponse,
    OverallStatus,
    VerificationResult,
)
from batch import store
from batch.orchestrator import start_batch

router = APIRouter(prefix="/jobs", tags=["jobs"])

#: How often a reconnecting SSE client polls for newly-completed labels.
_POLL_INTERVAL_SECONDS = 0.1


def _require_job(job_id: str) -> store.Job:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"job '{job_id}' not found",
        )
    return job


def _completed_results(job: store.Job) -> list[VerificationResult]:
    """Results filled in so far, skipping `None` placeholders for in-flight labels."""
    return [r for r in job.results if r is not None]


def _summarize(job: store.Job) -> BatchSummary:
    summary = BatchSummary()
    for result in _completed_results(job):
        if result.overall_status is OverallStatus.MATCH:
            summary.match += 1
        elif result.overall_status is OverallStatus.PARTIAL:
            summary.partial += 1
        elif result.overall_status is OverallStatus.FAIL:
            summary.fail += 1
        else:
            summary.error += 1
    return summary


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def job_status(job_id: str) -> JobStatusResponse:
    job = _require_job(job_id)
    return JobStatusResponse(
        job_id=job.job_id,
        state=job.state,
        completed=job.completed,
        total=job.total,
    )


@router.get("/{job_id}/results", response_model=JobResultsResponse)
def job_results(job_id: str) -> JobResultsResponse:
    job = _require_job(job_id)
    return JobResultsResponse(
        job_id=job.job_id,
        state=job.state,
        summary=_summarize(job),
        results=_completed_results(job),
    )


@router.get(
    "/{job_id}/export",
    summary="Export batch results as CSV",
    responses={200: {"content": {"text/csv": {}}, "description": "RFC 4180 CSV"}},
)
def job_export(job_id: str) -> Response:
    job = _require_job(job_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = ["filename", "overall_status", "confidence_score", *LABEL_FIELD_NAMES]
    writer.writerow(header)
    for result in _completed_results(job):
        by_field = {fc.field: fc for fc in result.fields}
        row = [
            result.filename or "",
            result.overall_status.value,
            f"{result.confidence_score:.1f}",
        ]
        for name in LABEL_FIELD_NAMES:
            if name == "government_warning":
                row.append("valid" if result.government_warning.valid else "invalid")
            else:
                fc = by_field.get(name)
                row.append(fc.status.value if fc else "")
        writer.writerow(row)

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="results_{job_id}.csv"'},
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _progress_event(progress: BatchProgress) -> str:
    event = "error" if progress.latest.overall_status is OverallStatus.ERROR else "progress"
    return _sse(event, progress.model_dump(mode="json"))


def _complete_event(job: store.Job) -> str:
    return _sse(
        "complete",
        {
            "job_id": job.job_id,
            "state": job.state.value,
            "completed": job.completed,
            "total": job.total,
            "summary": _summarize(job).model_dump(),
        },
    )


async def _stream_progress(job: store.Job) -> AsyncIterator[str]:
    """Emit `progress`/`error` events as labels finish, then `complete`.

    The first connection for a PENDING job drives the orchestrator directly,
    so the whole batch runs to completion within this one response. A
    reconnecting `EventSource` (job already PROCESSING or COMPLETED) instead
    polls `job.results` for labels it hasn't seen yet, replaying any it
    missed before catching up to new ones.
    """
    if job.state is JobState.PENDING:
        labels, job.labels = job.labels, []
        async for progress in start_batch(job.job_id, labels):
            yield _progress_event(progress)
    else:
        seen: set[int] = set()
        while True:
            for index, result in enumerate(job.results):
                if result is None or index in seen:
                    continue
                seen.add(index)
                yield _progress_event(
                    BatchProgress(job_id=job.job_id, completed=len(seen), total=job.total, latest=result)
                )
            if job.state is JobState.COMPLETED:
                break
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    yield _complete_event(job)


@router.get(
    "/{job_id}/stream",
    summary="Stream batch progress via Server-Sent Events",
    responses={200: {"content": {"text/event-stream": {}}, "description": "progress/error/complete SSE events"}},
)
async def job_stream(job_id: str) -> StreamingResponse:
    job = _require_job(job_id)
    return StreamingResponse(
        _stream_progress(job),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
