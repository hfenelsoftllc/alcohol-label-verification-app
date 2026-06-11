"""Pydantic request/response models — the typed API contract.

Every endpoint speaks these models; no untyped dicts cross the API boundary
(FedRAMP SI-10, Information Input Validation). Handlers in Phase 1 return
well-typed *stubs*; the real OCR/matching values are filled in across Phase 2.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# --- The six TTB-required label fields (+ the Government Warning). -----------
#: Canonical field keys used throughout extraction, matching, and export.
LABEL_FIELD_NAMES: tuple[str, ...] = (
    "brand",
    "class_type",
    "abv",
    "net_contents",
    "name_address",
    "country_of_origin",
    "government_warning",
)


class MatchStatus(str, Enum):
    """Per-field comparison outcome."""

    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NO_MATCH = "NO_MATCH"


class OverallStatus(str, Enum):
    """Aggregate outcome for a single label."""

    MATCH = "MATCH"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    ERROR = "ERROR"


class OcrEngine(str, Enum):
    """Which OCR backend produced the extraction."""

    CLAUDE_VISION = "claude_vision"
    TESSERACT = "tesseract"


class JobState(str, Enum):
    """Lifecycle of a batch job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApplicationData(BaseModel):
    """The values submitted in the COLA application (the expected truth)."""

    brand: str = Field(..., max_length=255, description="Brand name")
    class_type: str = Field(..., max_length=255, description="Class/type designation")
    abv: str = Field(..., max_length=64, description="Alcohol content, e.g. '40% Alc. by Vol.'")
    net_contents: str = Field(..., max_length=64, description="Net contents, e.g. '750 mL'")
    name_address: str = Field(..., max_length=512, description="Bottler name & address")
    country_of_origin: str = Field(..., max_length=255, description="Country of origin")
    government_warning: str = Field(..., max_length=2000, description="Government Warning text")


class ExtractedFields(BaseModel):
    """Fields read off the label by the OCR engine."""

    brand: str | None = None
    class_type: str | None = None
    abv: str | None = None
    net_contents: str | None = None
    name_address: str | None = None
    country_of_origin: str | None = None
    government_warning: str | None = None
    confidence_score: float = Field(0.0, ge=0.0, le=100.0)
    ocr_engine_used: OcrEngine = OcrEngine.CLAUDE_VISION


class ImageQualityReport(BaseModel):
    """Result of automated image quality assessment (ISSUE 2.2)."""

    score: float = Field(..., ge=0.0, le=100.0)
    issues: list[str] = Field(default_factory=list)


class FieldComparison(BaseModel):
    """Result of comparing one extracted field against the application value."""

    field: str
    extracted: str | None
    expected: str | None
    status: MatchStatus
    score: float = Field(..., ge=0.0, le=100.0)


class GovernmentWarningCheck(BaseModel):
    """Exact-match validation outcome for the Government Warning (ISSUE 2.5)."""

    valid: bool
    issues: list[str] = Field(default_factory=list)
    extracted_text: str | None = None
    expected_text: str | None = None


class MatchReport(BaseModel):
    """Result of comparing extracted label fields against application data (ISSUE 2.4)."""

    overall_status: OverallStatus
    fields: list[FieldComparison]


class VerificationResult(BaseModel):
    """Full verification outcome for a single label."""

    session_id: str
    overall_status: OverallStatus
    fields: list[FieldComparison]
    government_warning: GovernmentWarningCheck
    image_quality_score: float = Field(..., ge=0.0, le=100.0)
    quality_issues: list[str] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    ocr_engine_used: OcrEngine
    filename: str | None = None
    message: str | None = None


class VerifyRequest(BaseModel):
    """POST /verify body."""

    image: str = Field(..., description="Base64-encoded label image (optionally a data URL)")
    application_data: ApplicationData


class BatchSubmitResponse(BaseModel):
    """Response to a batch submission."""

    job_id: str
    state: JobState
    total: int


class JobStatusResponse(BaseModel):
    """Progress of a batch job."""

    job_id: str
    state: JobState
    completed: int
    total: int


class BatchSummary(BaseModel):
    """Aggregate counts across a completed batch."""

    match: int = 0
    partial: int = 0
    fail: int = 0
    error: int = 0


class JobResultsResponse(BaseModel):
    """Completed results for a batch job."""

    job_id: str
    state: JobState
    summary: BatchSummary
    results: list[VerificationResult]


class BatchProgress(BaseModel):
    """Progress event emitted as each label in a batch finishes (ISSUE 3.1)."""

    job_id: str
    completed: int
    total: int
    latest: VerificationResult


class ErrorResponse(BaseModel):
    """Uniform error envelope (FedRAMP SI-11 — error handling)."""

    error: str
    message: str
    request_id: str


class HealthResponse(BaseModel):
    """GET /health body."""

    status: str
    version: str
