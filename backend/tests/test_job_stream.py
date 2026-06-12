"""Tests for GET /jobs/{job_id}/stream (ISSUE 3.2)."""

from __future__ import annotations

import json

from app.models import ApplicationData, ExtractedFields, OcrEngine, OverallStatus
from batch import store
from tests.conftest import PNG_1X1
from tests.test_jobs import VALID_APPLICATION_ROW, _submit_batch


def _matching_extracted_fields() -> ExtractedFields:
    """An ExtractedFields that matches VALID_APPLICATION_ROW on every field."""
    return ExtractedFields(
        **{name: VALID_APPLICATION_ROW[name] for name in VALID_APPLICATION_ROW},
        confidence_score=98.0,
        ocr_engine_used=OcrEngine.CLAUDE_VISION,
    )


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((event, data))
    return events


def test_stream_emits_progress_then_complete(client, monkeypatch):
    monkeypatch.setattr("app.pipeline.extract_fields", lambda image_bytes: _matching_extracted_fields())

    job_id = _submit_batch(client, n_images=3).json()["job_id"]

    resp = client.get(f"/jobs/{job_id}/stream")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    progress_events = [data for event, data in events if event == "progress"]
    assert [p["completed"] for p in progress_events] == [1, 2, 3]
    assert all(p["total"] == 3 for p in progress_events)
    assert all(p["latest"]["overall_status"] == "MATCH" for p in progress_events)

    assert events[-1][0] == "complete"
    complete = events[-1][1]
    assert complete["job_id"] == job_id
    assert complete["state"] == "COMPLETED"
    assert complete["completed"] == 3
    assert complete["total"] == 3
    assert complete["summary"]["match"] == 3


def test_stream_emits_error_event_for_failed_label(client, session_id, monkeypatch):
    """The orchestrator's per-label validate_image_bytes guard is defense in
    depth alongside the /verify/batch upload check (ISSUE 3.6): a corrupt
    label is reported as an `error` SSE event without aborting the batch."""
    monkeypatch.setattr("app.pipeline.extract_fields", lambda image_bytes: _matching_extracted_fields())

    app_data = ApplicationData(**VALID_APPLICATION_ROW)
    job = store.create_job(total=2, session_id=session_id)
    job.labels = [
        store.LabelInput(image_bytes=PNG_1X1, application_data=app_data, filename="good.png"),
        store.LabelInput(image_bytes=b"not an image", application_data=app_data, filename="bad.png"),
    ]

    events = _parse_sse(client.get(f"/jobs/{job.job_id}/stream").text)

    by_event = [event for event, _ in events]
    assert by_event.count("error") == 1
    assert by_event.count("progress") == 1
    assert by_event[-1] == "complete"

    error_data = next(data for event, data in events if event == "error")
    assert error_data["latest"]["overall_status"] == OverallStatus.ERROR.value
    assert error_data["latest"]["filename"] == "bad.png"

    complete = events[-1][1]
    assert complete["summary"]["error"] == 1
    assert complete["summary"]["match"] == 1


def test_stream_reconnect_after_completion_replays_results(client, monkeypatch):
    monkeypatch.setattr("app.pipeline.extract_fields", lambda image_bytes: _matching_extracted_fields())

    job_id = _submit_batch(client, n_images=2).json()["job_id"]

    first = _parse_sse(client.get(f"/jobs/{job_id}/stream").text)
    assert [event for event, _ in first] == ["progress", "progress", "complete"]

    job = store.get_job(job_id)
    assert job.state.value == "COMPLETED"

    second = _parse_sse(client.get(f"/jobs/{job_id}/stream").text)
    assert [event for event, _ in second] == ["progress", "progress", "complete"]
    assert second[-1][1]["summary"] == first[-1][1]["summary"]


def test_stream_unknown_job_404(client):
    assert client.get("/jobs/does-not-exist/stream").status_code == 404
