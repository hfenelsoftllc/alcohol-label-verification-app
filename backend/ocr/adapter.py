"""OCR adapter — the system's most critical component.

`extract_fields(image_bytes) -> ExtractedFields` tries the Claude Vision API
first and falls back to local Tesseract when the API is unreachable, so the
system keeps working in a firewalled/air-gapped government environment.

FedRAMP: SA-9 (External System Services), SC-8 (Transmission Confidentiality).
"""

from __future__ import annotations

import base64
import io
import logging
import os

import anthropic
import pytesseract
from PIL import Image, UnidentifiedImageError

from app.models import ExtractedFields, OcrEngine
from ocr import parser

logger = logging.getLogger(__name__)

# --- Configuration (env-driven; the API key is never hardcoded). -------------
CLAUDE_VISION_MODEL = os.getenv("CLAUDE_VISION_MODEL", "claude-opus-4-8")
OCR_MODE = os.getenv("OCR_MODE", "auto").lower()
OCR_API_TIMEOUT_SECONDS = float(os.getenv("OCR_API_TIMEOUT_SECONDS", "30"))
_CLAUDE_CONFIDENCE = float(os.getenv("OCR_CLAUDE_CONFIDENCE", "95"))
_TESSERACT_CONFIDENCE = float(os.getenv("OCR_TESSERACT_CONFIDENCE", "60"))

_FIELD_NAMES = (
    "brand",
    "class_type",
    "abv",
    "net_contents",
    "name_address",
    "country_of_origin",
    "government_warning",
)

# Forced tool call → reliable structured extraction (no JSON-in-prose parsing).
_EXTRACTION_TOOL = {
    "name": "record_label_fields",
    "description": "Record the fields read from the alcohol beverage label.",
    "input_schema": {
        "type": "object",
        "properties": {
            "brand": {"type": ["string", "null"], "description": "Brand name"},
            "class_type": {"type": ["string", "null"], "description": "Class/type, e.g. Vodka, Cabernet Sauvignon"},
            "abv": {"type": ["string", "null"], "description": "Alcohol content exactly as printed, e.g. '40% Alc. by Vol.'"},
            "net_contents": {"type": ["string", "null"], "description": "Net contents, e.g. '750 mL'"},
            "name_address": {"type": ["string", "null"], "description": "Bottler/importer name and address"},
            "country_of_origin": {"type": ["string", "null"], "description": "Country of origin, e.g. 'Product of France'"},
            "government_warning": {"type": ["string", "null"], "description": "The Government Warning, transcribed verbatim"},
        },
        "required": list(_FIELD_NAMES),
    },
}

_PROMPT = (
    "You are reading a U.S. alcohol beverage label. Extract each requested field "
    "exactly as printed. Transcribe the Government Warning verbatim, preserving its "
    "wording and the ALL-CAPS 'GOVERNMENT WARNING' prefix. If a field is not present "
    "on the label, return null for it — do not guess."
)

_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}


class OcrError(Exception):
    """Raised when an OCR engine returns no usable result."""


def _detect_media_type(data: bytes) -> str:
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    for signature, media_type in _IMAGE_SIGNATURES.items():
        if data.startswith(signature):
            return media_type
    return "image/png"


def extract_fields(image_bytes: bytes) -> ExtractedFields:
    """Extract label fields, preferring Claude Vision and falling back to Tesseract."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if OCR_MODE == "local" or not api_key:
        if OCR_MODE != "local" and not api_key:
            logger.info("ANTHROPIC_API_KEY not set; using local Tesseract OCR.")
        return _extract_with_tesseract(image_bytes)

    try:
        return _extract_with_claude(image_bytes, api_key)
    except (anthropic.APITimeoutError, anthropic.APIConnectionError, TimeoutError, ConnectionError) as exc:
        # Firewalled environment: fail over immediately (no retries) to Tesseract.
        logger.warning("Claude Vision unavailable (%s); falling back to Tesseract.", type(exc).__name__)
        return _extract_with_tesseract(image_bytes)


def _extract_with_claude(image_bytes: bytes, api_key: str) -> ExtractedFields:
    # max_retries=0 so a network failure fails over to Tesseract immediately.
    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=OCR_API_TIMEOUT_SECONDS,
        max_retries=0,
    )
    response = client.messages.create(
        model=CLAUDE_VISION_MODEL,
        max_tokens=1024,
        tools=[_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_label_fields"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _detect_media_type(image_bytes),
                            "data": base64.standard_b64encode(image_bytes).decode(),
                        },
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ],
    )

    tool_input = next(
        (block.input for block in response.content if getattr(block, "type", None) == "tool_use"),
        None,
    )
    if tool_input is None:
        raise OcrError("Vision model did not return a structured extraction.")

    return ExtractedFields(
        **{name: tool_input.get(name) for name in _FIELD_NAMES},
        confidence_score=_CLAUDE_CONFIDENCE,
        ocr_engine_used=OcrEngine.CLAUDE_VISION,
    )


def _extract_with_tesseract(image_bytes: bytes) -> ExtractedFields:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        raw_text = pytesseract.image_to_string(image)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Degrade gracefully — never reject an image (per ADR-001 / SI-10).
        logger.warning("Tesseract could not read the image: %s", exc)
        return ExtractedFields(confidence_score=0.0, ocr_engine_used=OcrEngine.TESSERACT)

    return ExtractedFields(
        **parser.parse_raw_text(raw_text),
        confidence_score=_TESSERACT_CONFIDENCE,
        ocr_engine_used=OcrEngine.TESSERACT,
    )
