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
MAX_IMAGE_BYTES: int = int(os.getenv("MAX_IMAGE_MB", "20")) * 1024 * 1024

#: Maximum total image size for a single /verify/batch request. Configurable
#: via MAX_BATCH_MB (default 500 MB).
MAX_BATCH_BYTES: int = int(os.getenv("MAX_BATCH_MB", "500")) * 1024 * 1024

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
            detail="image is not valid base64",
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
            detail="unsupported media type: payload is not a recognized image",
        )
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"image exceeds the maximum size of {MAX_IMAGE_BYTES} bytes",
        )


def validate_batch_size(total_bytes: int) -> None:
    """Reject a batch whose cumulative image size exceeds MAX_BATCH_BYTES (413)."""
    if total_bytes > MAX_BATCH_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"batch exceeds the maximum total size of {MAX_BATCH_BYTES} bytes",
        )


def validate_upload(content_type: str | None, size: int | None, filename: str | None) -> None:
    """Validate a multipart UploadFile by declared content-type and size."""
    if not (content_type or "").lower().startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"file '{filename or '?'}' is not an image",
        )
    if size is not None and size > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"file '{filename or '?'}' exceeds the maximum size of {MAX_IMAGE_BYTES} bytes",
        )
