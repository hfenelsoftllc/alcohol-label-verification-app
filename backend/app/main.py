"""FastAPI application entrypoint.

Phase 1 (ISSUE 1.4) establishes the full route surface with Pydantic models and
stub handlers so frontend integration can begin against a stable contract. OCR,
matching, batching, and persistence are filled in across Phases 2-3.

OpenAPI docs are auto-generated at /docs.
"""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.audit import configure_logging, log_error, log_request_completed, log_request_received
from app.models import ErrorResponse, HealthResponse
from app.routers import jobs, verify

configure_logging()

app = FastAPI(
    title="Alcohol Label Verification API",
    version=__version__,
    description="TTB COLA automation PoC — label-vs-application verification.",
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a request id for correlation and emit structured audit logs (AU-2/AU-3)."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id

    log_request_received(request_id=request_id, endpoint=request.url.path, method=request.method)
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id

    log_request_completed(
        request_id=request_id,
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
        session_id=getattr(request.state, "session_id", None),
        ocr_engine_used=getattr(request.state, "ocr_engine_used", None),
    )
    return response


def _error(request: Request, code: int, error: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    body = ErrorResponse(error=error, message=message, request_id=request_id)
    return JSONResponse(status_code=code, content=body.model_dump())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Return a uniform error envelope instead of the default {"detail": ...}."""
    request_id = getattr(request.state, "request_id", "")
    log_error(request_id=request_id, endpoint=request.url.path, status_code=exc.status_code, error="http_error", message=str(exc.detail))
    return _error(request, exc.status_code, error="http_error", message=str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    log_error(request_id=request_id, endpoint=request.url.path, status_code=422, error="validation_error", message="request validation failed")
    return _error(request, 422, error="validation_error", message="request validation failed")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness/readiness probe. Used by the container HEALTHCHECK and compose."""
    return HealthResponse(status="ok", version=__version__)


app.include_router(verify.router)
app.include_router(jobs.router)
