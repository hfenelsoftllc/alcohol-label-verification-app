"""Single-label and batch verification endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile, status

from app.audit import log_match_completed, log_ocr_completed, log_ocr_started
from app.models import (
    BatchSubmitResponse,
    VerificationResult,
    VerifyRequest,
)
from app.stubs import build_stub_result
from app.validation import decode_base64_image, validate_image_bytes, validate_upload
from batch import store
from ocr.quality import assess_image_quality

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
    """Decode and validate the image, then return a (stub) verification result."""
    request_id = getattr(http_request.state, "request_id", "")
    image_bytes = decode_base64_image(payload.image)
    validate_image_bytes(image_bytes)
    image_quality = assess_image_quality(image_bytes)

    result = build_stub_result(payload.application_data, image_quality=image_quality)

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
    },
)
async def verify_batch(
    images: list[UploadFile] = File(..., description="Label image files"),
    application_csv: UploadFile = File(..., description="CSV of application data, one row per image"),
) -> BatchSubmitResponse:
    """Validate the uploaded files and register a batch job.

    Actual parallel processing is implemented by the orchestrator in ISSUE 3.1;
    here we only validate inputs and hand back a job_id to poll.
    """
    for image in images:
        validate_upload(image.content_type, image.size, image.filename)
    # application_csv is accepted and parsed by the orchestrator in Phase 3.
    job = store.create_job(total=len(images))
    return BatchSubmitResponse(job_id=job.job_id, state=job.state, total=job.total)
