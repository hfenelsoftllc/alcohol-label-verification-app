"""Single-label and batch verification endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile, status

from app.audit import log_match_completed, log_ocr_completed, log_ocr_started
from app.models import (
    BatchSubmitResponse,
    VerificationResult,
    VerifyRequest,
)
from app.pipeline import run_verification
from app.validation import decode_base64_image, validate_batch_size, validate_image_bytes, validate_upload
from batch import store
from batch.csv_input import parse_application_csv

router = APIRouter(tags=["verification"])


@router.post(
    "/verify",
    response_model=VerificationResult,
    summary="Verify a single label against its application data",
    responses={
        413: {"description": "Image exceeds the maximum size"},
        415: {"description": "Payload is not a recognized image"},
    },
)
def verify(payload: VerifyRequest, http_request: Request) -> VerificationResult:
    """Decode and validate the image, then run it through the verification pipeline."""
    request_id = getattr(http_request.state, "request_id", "")
    image_bytes = decode_base64_image(payload.image)
    validate_image_bytes(image_bytes)

    result = run_verification(image_bytes, payload.application_data)

    log_ocr_started(request_id=request_id, session_id=result.session_id)
    log_ocr_completed(
        request_id=request_id,
        session_id=result.session_id,
        ocr_engine_used=result.ocr_engine_used.value,
        confidence_score=result.confidence_score,
    )
    log_match_completed(request_id=request_id, session_id=result.session_id, overall_status=result.overall_status.value)

    http_request.state.session_id = result.session_id
    http_request.state.ocr_engine_used = result.ocr_engine_used.value
    return result


@router.post(
    "/verify/batch",
    response_model=BatchSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a batch of labels for processing",
    responses={
        413: {"description": "An image exceeds the maximum size"},
        415: {"description": "A submitted file is not an image"},
        422: {"description": "application_csv is missing columns, has the wrong row count, or an invalid value"},
    },
)
async def verify_batch(
    http_request: Request,
    images: list[UploadFile] = File(..., description="Label image files"),
    application_csv: UploadFile = File(..., description="CSV of application data, one row per image"),
) -> BatchSubmitResponse:
    """Validate the uploads, parse the CSV, and register a batch job.

    Processing is driven by the client opening
    `GET /jobs/{job_id}/stream` (ISSUE 3.2); this endpoint only validates
    inputs and hands back a job_id. The job is owned by the caller's
    session (ISSUE 3.7) — only that session can later access
    `/jobs/{job_id}/...`.
    """
    images_bytes: list[bytes] = []
    total_bytes = 0
    for image in images:
        validate_upload(image.content_type, image.size, image.filename)
        image_bytes = await image.read()
        validate_image_bytes(image_bytes)
        total_bytes += len(image_bytes)
        validate_batch_size(total_bytes)
        images_bytes.append(image_bytes)

    csv_bytes = await application_csv.read()
    application_rows = parse_application_csv(csv_bytes, expected_rows=len(images))

    job = store.create_job(total=len(images), session_id=http_request.state.auth_session_id)
    job.labels = [
        store.LabelInput(image_bytes=image_bytes, application_data=app_data, filename=image.filename)
        for image, image_bytes, app_data in zip(images, images_bytes, application_rows, strict=True)
    ]
    store.save_job(job)

    return BatchSubmitResponse(job_id=job.job_id, state=job.state, total=job.total)
