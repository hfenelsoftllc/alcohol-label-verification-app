"""Tests for the OCR adapter (Claude Vision + Tesseract fallback)."""

import anthropic
import httpx
import pytest

from app.models import OcrEngine
from ocr import adapter
from tests.conftest import PNG_1X1


class _ToolUseBlock:
    type = "tool_use"

    def __init__(self, data):
        self.input = data


class _Response:
    def __init__(self, data):
        self.content = [_ToolUseBlock(data)]


def _fake_anthropic(on_create):
    """Build a stand-in for anthropic.Anthropic whose messages.create runs on_create."""

    class _Messages:
        def create(self, **kwargs):
            return on_create(kwargs)

    class _Client:
        def __init__(self, **kwargs):
            self.messages = _Messages()

    return _Client


_EXTRACTED = {
    "brand": "Stone's Throw",
    "class_type": "Vodka",
    "abv": "40% Alc. by Vol.",
    "net_contents": "750 mL",
    "name_address": "Louisville, KY",
    "country_of_origin": "United States",
    "government_warning": "GOVERNMENT WARNING: ...",
}


def test_claude_vision_success(monkeypatch):
    monkeypatch.setattr(adapter, "OCR_MODE", "auto")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(adapter.anthropic, "Anthropic", _fake_anthropic(lambda _: _Response(_EXTRACTED)))

    result = adapter.extract_fields(PNG_1X1)

    assert result.ocr_engine_used == OcrEngine.CLAUDE_VISION
    assert result.brand == "Stone's Throw"
    assert result.abv == "40% Alc. by Vol."
    assert result.confidence_score > 0


def test_timeout_falls_back_to_tesseract(monkeypatch):
    monkeypatch.setattr(adapter, "OCR_MODE", "auto")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _raise_timeout(_):
        raise TimeoutError("vision API timed out")

    monkeypatch.setattr(adapter.anthropic, "Anthropic", _fake_anthropic(_raise_timeout))
    monkeypatch.setattr(
        adapter.pytesseract,
        "image_to_string",
        lambda _image: "BRAND 40% Alc. by Vol. 750 mL\nGOVERNMENT WARNING: ...",
    )

    result = adapter.extract_fields(PNG_1X1)

    assert result.ocr_engine_used == OcrEngine.TESSERACT
    assert result.abv == "40% Alc. by Vol."
    assert result.government_warning.startswith("GOVERNMENT WARNING")


def test_rate_limit_falls_back_to_tesseract(monkeypatch):
    monkeypatch.setattr(adapter, "OCR_MODE", "auto")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _raise_rate_limit(_):
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(429, request=request)
        raise anthropic.RateLimitError("rate limit exceeded", response=response, body=None)

    monkeypatch.setattr(adapter.anthropic, "Anthropic", _fake_anthropic(_raise_rate_limit))
    monkeypatch.setattr(
        adapter.pytesseract,
        "image_to_string",
        lambda _image: "BRAND 40% Alc. by Vol. 750 mL\nGOVERNMENT WARNING: ...",
    )

    result = adapter.extract_fields(PNG_1X1)

    assert result.ocr_engine_used == OcrEngine.TESSERACT
    assert result.abv == "40% Alc. by Vol."
    assert result.government_warning.startswith("GOVERNMENT WARNING")


def test_malformed_image_degrades_gracefully(monkeypatch):
    # Force the local path; a non-image payload must not raise.
    monkeypatch.setattr(adapter, "OCR_MODE", "local")

    result = adapter.extract_fields(b"this is not an image")

    assert result.ocr_engine_used == OcrEngine.TESSERACT
    assert result.confidence_score == 0.0
    assert result.brand is None


def test_local_mode_skips_api(monkeypatch):
    monkeypatch.setattr(adapter, "OCR_MODE", "local")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _fail(*args, **kwargs):
        raise AssertionError("Claude must not be called in local mode")

    monkeypatch.setattr(adapter.anthropic, "Anthropic", _fail)
    monkeypatch.setattr(adapter.pytesseract, "image_to_string", lambda _image: "")

    result = adapter.extract_fields(PNG_1X1)
    assert result.ocr_engine_used == OcrEngine.TESSERACT


def test_missing_api_key_uses_tesseract(monkeypatch):
    monkeypatch.setattr(adapter, "OCR_MODE", "auto")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(adapter.pytesseract, "image_to_string", lambda _image: "")

    result = adapter.extract_fields(PNG_1X1)
    assert result.ocr_engine_used == OcrEngine.TESSERACT


@pytest.mark.parametrize(
    "data,expected",
    [
        (PNG_1X1, "image/png"),
        (b"\xff\xd8\xff\xe0blah", "image/jpeg"),
        (b"GIF89a...", "image/gif"),
        (b"unknown", "image/png"),
    ],
)
def test_detect_media_type(data, expected):
    assert adapter._detect_media_type(data) == expected
