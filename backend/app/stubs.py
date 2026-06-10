"""Stub result construction for the Phase 1 skeleton.

These produce well-typed placeholder results so frontend integration can proceed
before the OCR (ISSUE 2.1-2.3) and matching (ISSUE 2.4-2.5) engines exist. Every
field is reported as a confident MATCH echoing the application data.
"""

from __future__ import annotations

import secrets

from app.models import (
    ApplicationData,
    FieldComparison,
    GovernmentWarningCheck,
    MatchStatus,
    OcrEngine,
    OverallStatus,
    VerificationResult,
)

_COMPARABLE_FIELDS = (
    "brand",
    "class_type",
    "abv",
    "net_contents",
    "name_address",
    "country_of_origin",
)

_STUB_NOTE = "stub result — OCR/matching engines land in Phase 2"


def new_session_id() -> str:
    return secrets.token_urlsafe(16)


def build_stub_result(
    application_data: ApplicationData,
    *,
    session_id: str | None = None,
    filename: str | None = None,
) -> VerificationResult:
    """Echo the application data back as a fully-matching stub result."""
    fields = [
        FieldComparison(
            field=name,
            extracted=getattr(application_data, name),
            expected=getattr(application_data, name),
            status=MatchStatus.MATCH,
            score=100.0,
        )
        for name in _COMPARABLE_FIELDS
    ]
    return VerificationResult(
        session_id=session_id or new_session_id(),
        overall_status=OverallStatus.MATCH,
        fields=fields,
        government_warning=GovernmentWarningCheck(valid=True),
        image_quality_score=100.0,
        confidence_score=100.0,
        ocr_engine_used=OcrEngine.CLAUDE_VISION,
        filename=filename,
        message=_STUB_NOTE,
    )
