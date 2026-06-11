"""Tests for the batch orchestrator (ISSUE 3.1)."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from app.models import ApplicationData, ExtractedFields, JobState, OcrEngine, OverallStatus
from batch import orchestrator, store
from batch.orchestrator import LabelInput
from tests.conftest import PNG_1X1


@pytest.fixture(autouse=True)
def _clear_store():
    store.clear()
    yield
    store.clear()


def _application_data(**overrides) -> ApplicationData:
    defaults = dict(
        brand="Stone's Throw",
        class_type="Vodka",
        abv="40% Alc. by Vol.",
        net_contents="750 mL",
        name_address="Stone's Throw Distillery, Louisville, KY",
        country_of_origin="United States",
        government_warning=(
            "GOVERNMENT WARNING: (1) According to the Surgeon General, women "
            "should not drink alcoholic beverages during pregnancy because of "
            "the risk of birth defects. (2) Consumption of alcoholic beverages "
            "impairs your ability to drive a car or operate machinery, and may "
            "cause health problems."
        ),
    )
    defaults.update(overrides)
    return ApplicationData(**defaults)


def _matching_extracted_fields(application_data: ApplicationData) -> ExtractedFields:
    """An ExtractedFields that matches `application_data` on every field."""
    return ExtractedFields(
        brand=application_data.brand,
        class_type=application_data.class_type,
        abv=application_data.abv,
        net_contents=application_data.net_contents,
        name_address=application_data.name_address,
        country_of_origin=application_data.country_of_origin,
        government_warning=application_data.government_warning,
        confidence_score=98.0,
        ocr_engine_used=OcrEngine.CLAUDE_VISION,
    )


def _run_batch(job_id: str, labels: list[LabelInput]):
    async def _collect():
        return [progress async for progress in orchestrator.start_batch(job_id, labels)]

    return asyncio.run(_collect())


def test_start_batch_processes_all_labels_in_order(monkeypatch):
    app_data = _application_data()
    monkeypatch.setattr(orchestrator, "extract_fields", lambda image_bytes: _matching_extracted_fields(app_data))

    job = store.create_job(total=3)
    labels = [
        LabelInput(image_bytes=PNG_1X1, application_data=app_data, filename=f"label_{i}.png") for i in range(3)
    ]

    progress_events = _run_batch(job.job_id, labels)

    assert [p.completed for p in progress_events] == [1, 2, 3]
    assert all(p.total == 3 for p in progress_events)
    assert all(p.job_id == job.job_id for p in progress_events)
    assert all(p.latest.overall_status == OverallStatus.MATCH for p in progress_events)

    assert job.state == JobState.COMPLETED
    assert job.completed == 3
    assert [r.filename for r in job.results] == ["label_0.png", "label_1.png", "label_2.png"]
    assert all(r.overall_status == OverallStatus.MATCH for r in job.results)
    assert all(r.government_warning.valid for r in job.results)


def test_concurrency_limit_respected(monkeypatch):
    monkeypatch.setenv("BATCH_MAX_WORKERS", "2")
    app_data = _application_data()

    lock = threading.Lock()
    counters = {"current": 0, "max": 0}

    def fake_extract_fields(image_bytes):
        with lock:
            counters["current"] += 1
            counters["max"] = max(counters["max"], counters["current"])
        time.sleep(0.05)
        with lock:
            counters["current"] -= 1
        return _matching_extracted_fields(app_data)

    monkeypatch.setattr(orchestrator, "extract_fields", fake_extract_fields)

    job = store.create_job(total=6)
    labels = [LabelInput(image_bytes=PNG_1X1, application_data=app_data) for _ in range(6)]

    _run_batch(job.job_id, labels)

    assert counters["max"] == 2
    assert job.state == JobState.COMPLETED
    assert job.completed == 6


def test_malformed_image_produces_error_without_aborting_batch(monkeypatch):
    app_data = _application_data()
    monkeypatch.setattr(orchestrator, "extract_fields", lambda image_bytes: _matching_extracted_fields(app_data))

    job = store.create_job(total=3)
    labels = [
        LabelInput(image_bytes=PNG_1X1, application_data=app_data, filename="good_1.png"),
        LabelInput(image_bytes=b"not an image", application_data=app_data, filename="bad.png"),
        LabelInput(image_bytes=PNG_1X1, application_data=app_data, filename="good_2.png"),
    ]

    progress_events = _run_batch(job.job_id, labels)

    assert len(progress_events) == 3
    assert job.state == JobState.COMPLETED
    assert job.completed == 3

    by_filename = {r.filename: r for r in job.results}
    assert by_filename["bad.png"].overall_status == OverallStatus.ERROR
    assert by_filename["bad.png"].government_warning.valid is False
    assert by_filename["bad.png"].message
    assert by_filename["good_1.png"].overall_status == OverallStatus.MATCH
    assert by_filename["good_2.png"].overall_status == OverallStatus.MATCH


def test_default_max_workers_is_ten():
    assert orchestrator.DEFAULT_MAX_WORKERS == 10
    assert orchestrator._max_workers() == 10


def test_start_batch_raises_for_unknown_job():
    async def _collect():
        return [progress async for progress in orchestrator.start_batch("does-not-exist", [])]

    with pytest.raises(ValueError):
        asyncio.run(_collect())


def test_load_300_labels_under_5s_average_no_crashes(monkeypatch):
    app_data = _application_data()
    monkeypatch.setattr(orchestrator, "extract_fields", lambda image_bytes: _matching_extracted_fields(app_data))

    total = 300
    job = store.create_job(total=total)
    labels = [
        LabelInput(image_bytes=PNG_1X1, application_data=app_data, filename=f"label_{i}.png")
        for i in range(total)
    ]

    start = time.perf_counter()
    progress_events = _run_batch(job.job_id, labels)
    elapsed = time.perf_counter() - start

    assert len(progress_events) == total
    assert job.state == JobState.COMPLETED
    assert job.completed == total
    assert len(job.results) == total
    assert all(r.overall_status == OverallStatus.MATCH for r in job.results)
    assert (elapsed / total) <= 5.0
