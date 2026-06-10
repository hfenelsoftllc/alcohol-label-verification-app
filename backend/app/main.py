"""FastAPI application entrypoint.

Phase 1 bootstrap (ISSUE 1.3): only the health endpoint is implemented so the
container has something to serve and the compose stack has a readiness signal.
The full route surface (/verify, /verify/batch, /jobs/*) is added in ISSUE 1.4.
"""

from fastapi import FastAPI

from app import __version__

app = FastAPI(
    title="Alcohol Label Verification API",
    version=__version__,
    description="TTB COLA automation PoC — label-vs-application verification.",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness/readiness probe. Used by the container HEALTHCHECK and compose."""
    return {"status": "ok", "version": __version__}
