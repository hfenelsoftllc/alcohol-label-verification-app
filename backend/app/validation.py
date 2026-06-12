"""Input validation for uploaded images (FedRAMP SI-10).

Enforces a maximum size (HTTP 413) and verifies the bytes are a recognized
image by magic number rather than trusting a client-supplied extension or
Content-Type alone (HTTP 415).
"""

from __future__ import annotations

import base64
import binascii
import os

from fastapi import HTTPException, status

#: Maximum accepted image size. Configurable via MAX_IMAGE_MB (default 20 MB).
MAX_IMAGE_MB: int = int(os.getenv("MAX_IMAGE_MB", "20"))
MAX_IMAGE_BYTES: int = MAX_IMAGE_MB * 1024 * 1024

#: Maximum total image size for a single /verify/batch request. Configurable
#: via MAX_BATCH_MB (default 500 MB).
MAX_BATCH_MB: int = int(os.getenv("MAX_BATCH_MB", "500"))
MAX_BATCH_BYTES: int = MAX_BATCH_MB * 1024 * 1024

#: Plain-language description of the accepted image formats (AC7 — no magic
#: byte / MIME jargon in user-facing messages).
_ACCEPTED_FORMATS = "JPG, PNG, GIF, BMP, TIFF, or WEBP"

#: Leading magic-byte signatures for the image formats we accept.
_IMAGE_SIGNATURES: tuple[bytes, ...] = (
    b"\xff\xd8\xff",            # JPEG
    b"\x89PNG\r\n\x1a\n",       # PNG
    b"GIF87a",                  # GIF
    b"GIF89a",                  # GIF
    b"BM",                      # BMP
    b"II*\x00",                 # TIFF (little-endian)
    b"MM\x00*",                 # TIFF (big-endian)
)


def decode_base64_image(data: str) -> bytes:
    """Decode a base64 image payload, tolerating an optional data-URL prefix."""
    payload = data.strip()
    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That image could not be read. Please try uploading it again.",
        ) from exc


def is_recognized_image(data: bytes) -> bool:
    """True if the bytes start with a supported image signature."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WEBP container
        return True
    return any(data.startswith(sig) for sig in _IMAGE_SIGNATURES)


def validate_image_bytes(data: bytes) -> None:
    """Reject non-images (415) and oversized images (413)."""
    if not is_recognized_image(data):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"That file isn't a supported image type. Please upload a {_ACCEPTED_FORMATS} image.",
        )
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"That image is larger than {MAX_IMAGE_MB} MB. Please choose a smaller file.",
        )


def validate_batch_size(total_bytes: int) -> None:
    """Reject a batch whose cumulative image size exceeds MAX_BATCH_BYTES (413)."""
    if total_bytes > MAX_BATCH_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"This batch is larger than {MAX_BATCH_MB} MB in total. Please upload fewer or smaller images.",
        )


def validate_upload(content_type: str | None, size: int | None, filename: str | None) -> None:
    """Validate a multipart UploadFile by declared content-type and size."""
    name = filename or "that file"
    if not (content_type or "").lower().startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"'{name}' isn't a supported image type. Please upload a {_ACCEPTED_FORMATS} image.",
        )
    if size is not None and size > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"'{name}' is larger than {MAX_IMAGE_MB} MB. Please choose a smaller file.",
        )
