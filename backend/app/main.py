"""FastAPI application entrypoint.

Phase 1 (ISSUE 1.4) establishes the full route surface with Pydantic models and
stub handlers so frontend integration can begin against a stable contract. OCR,
matching, batching, and persistence are filled in across Phases 2-3.

OpenAPI docs are auto-generated at /docs.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.models import ErrorResponse, HealthResponse
from app.routers import jobs, verify

app = FastAPI(
    title="Alcohol Label Verification API",
    version=__version__,
    description="TTB COLA automation PoC — label-vs-application verification.",
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a request id for correlation; surfaced in errors and a response header."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _error(request: Request, code: int, error: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    body = ErrorResponse(error=error, message=message, request_id=request_id)
    return JSONResponse(status_code=code, content=body.model_dump())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Return a uniform error envelope instead of the default {"detail": ...}."""
    return _error(request, exc.status_code, error="http_error", message=str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(request, 422, error="validation_error", message="request validation failed")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness/readiness probe. Used by the container HEALTHCHECK and compose."""
    return HealthResponse(status="ok", version=__version__)


app.include_router(verify.router)
app.include_router(jobs.router)
