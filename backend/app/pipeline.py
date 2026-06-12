"""Verification pipeline (ISSUE 4.4).

`run_verification` is the single entry point shared by `POST /verify` (one
label) and the batch orchestrator (many labels): it assesses image quality,
runs OCR, compares the result against the application data, and validates
the Government Warning. It never raises — an image OpenCV/Pillow cannot
decode at all (AC3), or any other unexpected failure during OCR/matching
(AC4), degrades to a plain-language `ERROR` result instead (FedRAMP SI-17,
Fail-Safe Procedures).

OCR API timeouts (AC2) are handled one layer down, in
`ocr.adapter.extract_fields`, which falls back to Tesseract with a lower
`confidence_score` — `run_verification` just reflects whatever
`ExtractedFields` it gets back.
"""

from __future__ import annotations

import logging
import secrets

from app.models import ApplicationData, GovernmentWarningCheck, OcrEngine, OverallStatus, VerificationResult
from matching import engine
from matching.exact_validator import validate_government_warning
from ocr.adapter import extract_fields
from ocr.preprocessor import maybe_preprocess
from ocr.quality import assess_image_quality

logger = logging.getLogger(__name__)

#: AC3 — exact wording required when the image can't be decoded at all.
UNREADABLE_IMAGE_MESSAGE = "Image quality too low to extract any fields"

#: AC4 — any other unexpected failure during OCR or matching.
PROCESSING_ERROR_MESSAGE = "This label could not be processed due to an unexpected error. Please try again."

#: A label whose bytes don't pass basic image validation (defense-in-depth;
#: callers normally reject these before reaching the pipeline).
INVALID_IMAGE_MESSAGE = "This file could not be read as an image. Please check the file and try again."


def new_session_id() -> str:
    return secrets.token_urlsafe(16)


def run_verification(
    image_bytes: bytes,
    application_data: ApplicationData,
    *,
    filename: str | None = None,
    session_id: str | None = None,
) -> VerificationResult:
    """Run one label through quality assessment, OCR, matching, and the
    Government Warning check.

    `image_bytes` is assumed to have already passed
    `app.validation.validate_image_bytes` (recognized format, within the size
    limit) — this function handles the next failure tier: bytes that look
    like an image but can't actually be decoded, and unexpected failures in
    the OCR/matching engines.
    """
    image_quality = assess_image_quality(image_bytes)

    if image_quality.issues == ["unreadable"]:
        return _error_result(
            session_id=session_id,
            filename=filename,
            image_quality_score=image_quality.score,
            quality_issues=image_quality.issues,
            warning_issues=["UNREADABLE_IMAGE"],
            message=UNREADABLE_IMAGE_MESSAGE,
        )

    try:
        ocr_input = maybe_preprocess(image_bytes, image_quality.score)
        extracted = extract_fields(ocr_input)
        match_report = engine.compare(extracted, application_data)
        warning_check = validate_government_warning(extracted.government_warning, application_data.government_warning)
    except Exception:
        logger.exception("Unexpected failure during OCR/matching.")
        return _error_result(
            session_id=session_id,
            filename=filename,
            image_quality_score=image_quality.score,
            quality_issues=image_quality.issues,
            warning_issues=["PROCESSING_ERROR"],
            message=PROCESSING_ERROR_MESSAGE,
        )

    overall_status = match_report.overall_status
    if not warning_check.valid:
        overall_status = OverallStatus.FAIL

    return VerificationResult(
        session_id=session_id or new_session_id(),
        overall_status=overall_status,
        fields=match_report.fields,
        government_warning=warning_check,
        image_quality_score=image_quality.score,
        quality_issues=image_quality.issues,
        confidence_score=extracted.confidence_score,
        ocr_engine_used=extracted.ocr_engine_used,
        filename=filename,
    )


def _error_result(
    *,
    session_id: str | None,
    filename: str | None,
    image_quality_score: float,
    quality_issues: list[str],
    warning_issues: list[str],
    message: str,
) -> VerificationResult:
    return VerificationResult(
        session_id=session_id or new_session_id(),
        overall_status=OverallStatus.ERROR,
        fields=[],
        government_warning=GovernmentWarningCheck(valid=False, issues=warning_issues),
        image_quality_score=image_quality_score,
        quality_issues=quality_issues,
        confidence_score=0.0,
        # No OCR engine ran; TESSERACT is the offline default and the closest
        # available value to "none" without adding a new enum member.
        ocr_engine_used=OcrEngine.TESSERACT,
        filename=filename,
        message=message,
    )
