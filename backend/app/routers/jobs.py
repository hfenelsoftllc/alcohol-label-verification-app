"""Batch job status, results, and export endpoints."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, HTTPException, Response, status

from app.models import (
    LABEL_FIELD_NAMES,
    BatchSummary,
    JobResultsResponse,
    JobStatusResponse,
    OverallStatus,
)
from batch import store

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _require_job(job_id: str) -> store.Job:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"job '{job_id}' not found",
        )
    return job


def _summarize(job: store.Job) -> BatchSummary:
    summary = BatchSummary()
    for result in job.results:
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
        results=job.results,
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
    for result in job.results:
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
