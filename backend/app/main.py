"""FastAPI application entrypoint.

Phase 1 (ISSUE 1.4) establishes the full route surface with Pydantic models and
stub handlers so frontend integration can begin against a stable contract. OCR,
matching, batching, and persistence are filled in across Phases 2-3.

OpenAPI docs are auto-generated at /docs.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__, session
from app.audit import configure_logging, log_error, log_request_completed, log_request_received
from app.models import ErrorResponse, HealthResponse
from app.routers import jobs, verify

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Alcohol Label Verification API",
    version=__version__,
    description="TTB COLA automation PoC — label-vs-application verification.",
)


@app.middleware("http")
async def session_authentication(request: Request, call_next):
    """Validate or issue the browser session cookie (ISSUE 3.7).

    FedRAMP IA-2/SC-23/AC-3: every request to `/jobs/*` must carry a valid
    session cookie (403 otherwise, AC2); all other paths transparently mint
    one on first visit (AC1) so the cookie exists before the client's first
    batch submission. Registered before `add_request_id` below, which
    becomes the outer middleware — so `request.state.request_id` is already
    set, and 403s here still get request-id/audit logging (AC3).
    """
    session_id = session.validate_cookie(request.cookies.get(session.COOKIE_NAME))
    issue_cookie = session_id is None and not request.url.path.startswith("/jobs/")

    if session_id is None:
        if request.url.path.startswith("/jobs/"):
            request_id = getattr(request.state, "request_id", "")
            log_error(
                request_id=request_id,
                endpoint=request.url.path,
                status_code=status.HTTP_403_FORBIDDEN,
                error="forbidden",
                message="missing or invalid session",
            )
            return _error(request, status.HTTP_403_FORBIDDEN, "forbidden", "missing or invalid session")
        session_id = session.create().session_id

    request.state.auth_session_id = session_id

    response = await call_next(request)

    if issue_cookie:
        response.set_cookie(session.COOKIE_NAME, session.sign(session_id), **session.cookie_kwargs())

    return response


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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so an unexpected error never reaches the client as a raw
    stack trace (FedRAMP SI-17, Fail-Safe Procedures). The real exception is
    logged server-side via `logger.exception` for incident response (IR-8);
    the client only sees a generic, plain-language message."""
    request_id = getattr(request.state, "request_id", "")
    logger.exception("Unhandled exception", exc_info=exc)
    log_error(request_id=request_id, endpoint=request.url.path, status_code=500, error="internal_error", message=str(exc))
    return _error(request, status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred. Please try again.")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness/readiness probe. Used by the container HEALTHCHECK and compose."""
    return HealthResponse(status="ok", version=__version__)


app.include_router(verify.router)
app.include_router(jobs.router)
