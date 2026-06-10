"""Tests for structured audit logging (ISSUE 2.7).

FedRAMP: AU-2 (Event Logging), AU-3 (Content of Audit Records),
AU-9 (Protection of Audit Information).
"""

from __future__ import annotations

import json

from app import audit
from tests.conftest import PNG_1X1_B64


def _events(raw: str) -> list[dict]:
    events = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def test_verify_request_completed_has_required_fields(client, application_data, capsys):
    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    assert resp.status_code == 200

    completed = next(e for e in _events(capsys.readouterr().out) if e["event"] == "request_completed")

    for field in ("timestamp", "request_id", "endpoint", "status_code", "duration_ms", "session_id", "ocr_engine_used"):
        assert field in completed, f"missing field: {field}"

    assert completed["endpoint"] == "/verify"
    assert completed["status_code"] == 200
    assert completed["ocr_engine_used"] == "claude_vision"
    assert completed["request_id"] == resp.headers["X-Request-ID"]


def test_verify_emits_pipeline_events(client, application_data, capsys):
    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    body = resp.json()

    events = _events(capsys.readouterr().out)
    event_names = {e["event"] for e in events}
    assert {"request_received", "ocr_started", "ocr_completed", "match_completed", "request_completed"} <= event_names

    ocr_completed = next(e for e in events if e["event"] == "ocr_completed")
    assert ocr_completed["session_id"] == body["session_id"]
    assert ocr_completed["ocr_engine_used"] == "claude_vision"

    match_completed = next(e for e in events if e["event"] == "match_completed")
    assert match_completed["session_id"] == body["session_id"]
    assert match_completed["overall_status"] == body["overall_status"]


def test_logs_never_contain_pii(client, application_data, capsys):
    resp = client.post("/verify", json={"image": PNG_1X1_B64, "application_data": application_data})
    assert resp.status_code == 200

    raw = capsys.readouterr().out
    for event in _events(raw):
        assert "image_bytes" not in event
        assert "base64_data" not in event

    assert PNG_1X1_B64 not in raw
    assert application_data["name_address"] not in raw


def test_error_response_logs_request_error(client, application_data, capsys):
    resp = client.post("/verify", json={"image": "!!!not base64!!!", "application_data": application_data})
    assert resp.status_code == 400

    events = _events(capsys.readouterr().out)
    error_event = next(e for e in events if e["event"] == "request_error")
    assert error_event["status_code"] == 400
    assert error_event["error"] == "http_error"

    completed = next(e for e in events if e["event"] == "request_completed")
    assert completed["status_code"] == 400


def test_log_session_expired_helper(capsys):
    audit.log_session_expired(session_id="abc123")

    event = next(e for e in _events(capsys.readouterr().out) if e["event"] == "session_expired")
    assert event["session_id"] == "abc123"


def test_log_level_filters_below_threshold(monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    try:
        audit.configure_logging()
        audit.log_ocr_started(request_id="r1", session_id="s1")  # INFO -> suppressed
        audit.log_error(request_id="r1", endpoint="/verify", status_code=500, error="boom", message="boom")  # WARNING -> emitted
    finally:
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        audit.configure_logging()

    event_names = {e["event"] for e in _events(capsys.readouterr().out)}
    assert "ocr_started" not in event_names
    assert "request_error" in event_names
