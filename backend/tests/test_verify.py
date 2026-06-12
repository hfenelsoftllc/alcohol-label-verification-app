"""Tests for the single-label /verify endpoint."""

import base64

from app.models import ExtractedFields, OcrEngine
from tests.conftest import PNG_1X1_B64, UNREADABLE_PNG_B64


def _matching_extracted_fields(application_data: dict, *, confidence_score=98.0, ocr_engine_used=OcrEngine.CLAUDE_VISION) -> ExtractedFields:
    """An ExtractedFields that matches `application_data` on every field."""
    return ExtractedFields(
        brand=application_data["brand"],
        class_type=application_data["class_type"],
        abv=application_data["abv"],
        net_contents=application_data["net_contents"],
        name_address=application_data["name_address"],
        country_of_origin=application_data["country_of_origin"],
        government_warning=application_data["government_warning"],
        confidence_score=confidence_score,
        ocr_engine_used=ocr_engine_used,
    )


def test_verify_happy_path(client, application_data, monkeypatch):
    monkeypatch.setattr("app.pipeline.extract_fields", lambda image_bytes: _matching_extracted_fields(application_data))

    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_status"] == "MATCH"
    assert {f["field"] for f in body["fields"]} == {
        "brand",
        "class_type",
        "abv",
        "net_contents",
        "name_address",
        "country_of_origin",
    }
    assert all(f["status"] == "MATCH" for f in body["fields"])
    assert body["government_warning"]["valid"] is True
    assert body["ocr_engine_used"] == "claude_vision"


def test_verify_reflects_ocr_timeout_fallback(client, application_data, monkeypatch):
    """ISSUE 4.4 AC2 — when OCR falls back to Tesseract, /verify reflects
    that engine and its (lower) confidence score rather than hiding it."""
    monkeypatch.setattr(
        "app.pipeline.extract_fields",
        lambda image_bytes: _matching_extracted_fields(application_data, confidence_score=60.0, ocr_engine_used=OcrEngine.TESSERACT),
    )

    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ocr_engine_used"] == "tesseract"
    assert body["confidence_score"] == 60.0


def test_verify_unreadable_image_returns_error(client, application_data):
    """ISSUE 4.4 AC3 — a completely undecodable image returns an ERROR
    result with a plain-language message, not a crash."""
    resp = client.post("/verify", json={"image": UNREADABLE_PNG_B64, "application_data": application_data})
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_status"] == "ERROR"
    assert body["message"] == "Image quality too low to extract any fields"
    assert body["fields"] == []
    assert body["government_warning"]["valid"] is False


def test_unhandled_exception_returns_structured_500(client_no_raise, application_data, monkeypatch):
    """ISSUE 4.4 AC1 — an unexpected exception never reaches the client as a
    raw stack trace; the global handler returns {error, message, request_id}."""

    def _boom(image_bytes):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.pipeline.assess_image_quality", _boom)

    resp = client_no_raise.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "internal_error"
    assert body["message"] == "An unexpected error occurred. Please try again."
    assert "boom" not in body["message"]
    assert body["request_id"]


def test_verify_rejects_non_image_415(client, application_data):
    not_an_image = base64.b64encode(b"this is plainly text, not an image").decode()
    resp = client.post("/verify", json={"image": not_an_image, "application_data": application_data})
    assert resp.status_code == 415
    assert resp.json()["error"] == "http_error"


def test_verify_rejects_oversize_413(client, application_data, monkeypatch):
    # Shrink the limit so the tiny PNG counts as oversized.
    monkeypatch.setattr("app.validation.MAX_IMAGE_BYTES", 10)
    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    assert resp.status_code == 413


def test_verify_rejects_bad_base64_400(client, application_data):
    resp = client.post("/verify", json={"image": "!!!not base64!!!", "application_data": application_data})
    assert resp.status_code == 400


def test_verify_requires_all_fields_422(client):
    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": {"brand": "X"}})
    assert resp.status_code == 422
    assert resp.json()["error"] == "validation_error"


def test_response_has_request_id_header(client, application_data):
    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    assert resp.headers.get("X-Request-ID")
