"""Tests for the single-label /verify endpoint."""

import base64

from tests.conftest import PNG_1X1_B64


def test_verify_happy_path(client, application_data):
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
