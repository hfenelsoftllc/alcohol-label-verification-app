"""Structured audit logging (ISSUE 2.7).

Configures structlog to emit one JSON object per line to stdout — the only
sink, per Docker logging best practice — and exposes a small set of helper
functions, one per audited event type. Each helper has an explicit
keyword-only signature, so raw image bytes, base64 payloads, and the Name &
Address value can never reach a log line by accident.

FedRAMP: AU-2 (Event Logging), AU-3 (Content of Audit Records),
AU-9 (Protection of Audit Information).
"""

from __future__ import annotations

import logging
import os

import structlog

_LOGGER_NAME = "audit"


def configure_logging() -> None:
    """Configure structlog for single-line JSON logs to stdout.

    The level is controlled by the LOG_LEVEL env var (default INFO, AU-2).
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def _logger() -> structlog.BoundLogger:
    return structlog.get_logger(_LOGGER_NAME)


def log_request_received(*, request_id: str, endpoint: str, method: str) -> None:
    """An API request was received."""
    _logger().info("request_received", request_id=request_id, endpoint=endpoint, method=method)


def log_request_completed(
    *,
    request_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    session_id: str | None = None,
    ocr_engine_used: str | None = None,
) -> None:
    """An API request finished — the primary per-request audit record (AU-3)."""
    _logger().info(
        "request_completed",
        request_id=request_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        session_id=session_id,
        ocr_engine_used=ocr_engine_used,
    )


def log_ocr_started(*, request_id: str, session_id: str) -> None:
    """OCR extraction started for a label image."""
    _logger().info("ocr_started", request_id=request_id, session_id=session_id)


def log_ocr_completed(*, request_id: str, session_id: str, ocr_engine_used: str, confidence_score: float) -> None:
    """OCR extraction finished, recording which engine produced the result."""
    _logger().info(
        "ocr_completed",
        request_id=request_id,
        session_id=session_id,
        ocr_engine_used=ocr_engine_used,
        confidence_score=confidence_score,
    )


def log_match_completed(*, request_id: str, session_id: str, overall_status: str) -> None:
    """Field-matching against the application data finished."""
    _logger().info("match_completed", request_id=request_id, session_id=session_id, overall_status=overall_status)


def log_error(*, request_id: str, endpoint: str, status_code: int, error: str, message: str) -> None:
    """An error response was returned to the client."""
    _logger().warning(
        "request_error",
        request_id=request_id,
        endpoint=endpoint,
        status_code=status_code,
        error=error,
        message=message,
    )


def log_session_expired(*, session_id: str) -> None:
    """A session/job was reaped after its TTL expired (ISSUE 3.5)."""
    _logger().info("session_expired", session_id=session_id)
