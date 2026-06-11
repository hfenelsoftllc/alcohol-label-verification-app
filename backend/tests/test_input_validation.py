"""Input validation, sanitization, and fuzz tests (ISSUE 3.6).

FedRAMP SI-10 (Information Input Validation) / SI-16 (Memory Protection):
malformed input must never crash the server (HTTP 500). Every response is
either a successful result or a well-formed 4xx `ErrorResponse`.
"""

from __future__ import annotations

import base64
import csv
import io

import pytest

from app.models import LABEL_FIELD_NAMES, ApplicationData
from tests.conftest import PNG_1X1, PNG_1X1_B64


def _csv_bytes(rows: list[dict], fieldnames: list[str] | None = None) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames or list(LABEL_FIELD_NAMES))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# AC4 — string fields are stripped of leading/trailing whitespace.
# ---------------------------------------------------------------------------


def test_application_data_strips_whitespace(application_data):
    padded = {k: f"  {v}\t\n" for k, v in application_data.items()}
    data = ApplicationData(**padded)
    for k, v in application_data.items():
        assert getattr(data, k) == v


# ---------------------------------------------------------------------------
# AC3 — application_csv rejects unrecognized column names.
# ---------------------------------------------------------------------------


def test_batch_rejects_csv_unknown_column_422(client, application_data):
    csv_bytes = _csv_bytes(
        [dict(application_data, extra_column="???")],
        fieldnames=[*LABEL_FIELD_NAMES, "extra_column"],
    )
    files = [("images", ("label_0.png", PNG_1X1, "image/png"))]
    files.append(("application_csv", ("data.csv", csv_bytes, "text/csv")))

    resp = client.post("/verify/batch", files=files)

    assert resp.status_code == 422
    assert "extra_column" in resp.json()["message"]


# ---------------------------------------------------------------------------
# AC1 — /verify/batch images are validated by magic byte, not declared
# Content-Type alone.
# ---------------------------------------------------------------------------


def test_batch_rejects_fake_image_with_image_content_type_415(client, application_data):
    files = [("images", ("label_0.png", b"not a real image", "image/png"))]
    files.append(("application_csv", ("data.csv", _csv_bytes([application_data]), "text/csv")))

    resp = client.post("/verify/batch", files=files)

    assert resp.status_code == 415


# ---------------------------------------------------------------------------
# AC2 — /verify/batch enforces a cumulative size cap across all images.
# ---------------------------------------------------------------------------


def test_batch_rejects_oversize_total_413(client, application_data, monkeypatch):
    # The first image alone fits exactly; the second pushes the total over.
    monkeypatch.setattr("app.validation.MAX_BATCH_BYTES", len(PNG_1X1))
    files = [("images", (f"label_{i}.png", PNG_1X1, "image/png")) for i in range(2)]
    files.append(("application_csv", ("data.csv", _csv_bytes([application_data] * 2), "text/csv")))

    resp = client.post("/verify/batch", files=files)

    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# AC8 — fuzzing: malformed inputs must never crash the server (no 5xx).
# ---------------------------------------------------------------------------

VERIFY_FUZZ_CASES = {
    "empty_image_string": lambda ad: {"image": "", "application_data": ad},
    "whitespace_only_image": lambda ad: {"image": "   ", "application_data": ad},
    "data_url_with_no_comma": lambda ad: {"image": "data:image/png;base64", "application_data": ad},
    "huge_base64_garbage": lambda ad: {
        "image": base64.b64encode(b"\x00" * 100_000).decode(),
        "application_data": ad,
    },
    "image_is_null": lambda ad: {"image": None, "application_data": ad},
    "image_is_number": lambda ad: {"image": 12345, "application_data": ad},
    "image_is_object": lambda ad: {"image": {"foo": "bar"}, "application_data": ad},
    "application_data_is_null": lambda ad: {"image": PNG_1X1_B64, "application_data": None},
    "application_data_missing_field": lambda ad: {
        "image": PNG_1X1_B64,
        "application_data": {k: v for k, v in ad.items() if k != "government_warning"},
    },
    "brand_too_long": lambda ad: {"image": PNG_1X1_B64, "application_data": {**ad, "brand": "x" * 1000}},
    "abv_is_number": lambda ad: {"image": PNG_1X1_B64, "application_data": {**ad, "abv": 40}},
    "brand_is_null": lambda ad: {"image": PNG_1X1_B64, "application_data": {**ad, "brand": None}},
    "brand_has_control_chars": lambda ad: {
        "image": PNG_1X1_B64,
        "application_data": {**ad, "brand": "Stone\x00's\x01Throw"},
    },
    "brand_has_unicode_emoji": lambda ad: {
        "image": PNG_1X1_B64,
        "application_data": {**ad, "brand": "\U0001f377\U0001f37e Wine Co. 日本語"},
    },
    "extra_unexpected_top_level_field": lambda ad: {
        "image": PNG_1X1_B64,
        "application_data": ad,
        "unexpected": "field",
    },
    "empty_body": lambda ad: {},
}


@pytest.mark.parametrize("build_payload", VERIFY_FUZZ_CASES.values(), ids=VERIFY_FUZZ_CASES.keys())
def test_verify_fuzz_never_crashes(client, application_data, build_payload):
    resp = client.post("/verify", json=build_payload(application_data))
    assert resp.status_code < 500


def _missing_images(ad: dict) -> list[tuple]:
    return [("application_csv", ("data.csv", _csv_bytes([ad]), "text/csv"))]


def _non_utf8_csv(ad: dict) -> list[tuple]:
    return [
        ("images", ("label_0.png", PNG_1X1, "image/png")),
        ("application_csv", ("data.csv", b"\xff\xfe\x00\x01invalid-utf8", "text/csv")),
    ]


def _empty_csv(ad: dict) -> list[tuple]:
    return [
        ("images", ("label_0.png", PNG_1X1, "image/png")),
        ("application_csv", ("data.csv", b"", "text/csv")),
    ]


def _duplicate_csv_columns(ad: dict) -> list[tuple]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["brand", "brand", "class_type", "abv", "net_contents", "name_address", "country_of_origin", "government_warning"])
    writer.writerow([ad["brand"], ad["brand"], ad["class_type"], ad["abv"], ad["net_contents"], ad["name_address"], ad["country_of_origin"], ad["government_warning"]])
    return [
        ("images", ("label_0.png", PNG_1X1, "image/png")),
        ("application_csv", ("data.csv", buffer.getvalue().encode("utf-8"), "text/csv")),
    ]


def _path_traversal_filename(ad: dict) -> list[tuple]:
    return [
        ("images", ("../../etc/passwd.png", PNG_1X1, "image/png")),
        ("application_csv", ("data.csv", _csv_bytes([ad]), "text/csv")),
    ]


BATCH_FUZZ_CASES = {
    "missing_images_field": _missing_images,
    "non_utf8_csv": _non_utf8_csv,
    "empty_csv": _empty_csv,
    "duplicate_csv_columns": _duplicate_csv_columns,
    "path_traversal_filename": _path_traversal_filename,
}


@pytest.mark.parametrize("build_files", BATCH_FUZZ_CASES.values(), ids=BATCH_FUZZ_CASES.keys())
def test_batch_fuzz_never_crashes(client, application_data, build_files):
    resp = client.post("/verify/batch", files=build_files(application_data))
    assert resp.status_code < 500
