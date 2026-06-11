"""Synthetic 300-label fixtures for the ISSUE 4.2 load test.

This repo has no real-world label photos (the same constraint documented in
``docs/fedramp/PREPROCESSING-AB-TEST.md`` for ISSUE 4.1), so the load test
generates a small synthetic "label photo" PNG -- the same checkerboard-pattern
generator family used by ``backend/scripts/preprocessing_ab_test.py`` and
``backend/tests/test_preprocessor.py`` -- reused for every label, plus a
matching ``application_csv``.

Must be imported after ``backend`` has been added to ``sys.path`` (see
``load_test.py``), since it imports ``app.models.LABEL_FIELD_NAMES`` to keep
the CSV columns in sync with the API's validation.
"""

from __future__ import annotations

import csv
import io

import cv2
import numpy as np

from app.models import LABEL_FIELD_NAMES

#: A row of application data that satisfies every required ApplicationData
#: field (mirrors backend/tests/test_jobs.py::VALID_APPLICATION_ROW).
APPLICATION_ROW: dict[str, str] = {
    "brand": "Stone's Throw",
    "class_type": "Vodka",
    "abv": "40% Alc. by Vol.",
    "net_contents": "750 mL",
    "name_address": "Stone's Throw Distillery, Louisville, KY",
    "country_of_origin": "United States",
    "government_warning": (
        "GOVERNMENT WARNING: (1) According to the Surgeon General, women "
        "should not drink alcoholic beverages during pregnancy because of "
        "the risk of birth defects. (2) Consumption of alcoholic beverages "
        "impairs your ability to drive a car or operate machinery, and may "
        "cause health problems."
    ),
}


def _checkerboard(size: int = 300, cell: int = 40, square: int = 15, light: int = 200, dark: int = 50) -> np.ndarray:
    """A scattered grid of small dark squares -- simulates text on a label."""
    image = np.full((size, size), light, dtype=np.uint8)
    for y in range(cell // 2, size, cell):
        for x in range(cell // 2, size, cell):
            image[y : y + square, x : x + square] = dark
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


def label_image_bytes() -> bytes:
    """One small synthetic "label photo" PNG, reused for every label."""
    ok, buf = cv2.imencode(".png", _checkerboard())
    assert ok
    return buf.tobytes()


def application_csv_bytes(n_rows: int) -> bytes:
    """A valid ``application_csv`` with `n_rows` identical rows."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=LABEL_FIELD_NAMES)
    writer.writeheader()
    for _ in range(n_rows):
        writer.writerow(APPLICATION_ROW)
    return buffer.getvalue().encode("utf-8")


def build_batch_files(n_labels: int) -> list[tuple[str, tuple[str, bytes, str]]]:
    """The multipart ``files`` payload for ``POST /verify/batch``: `n_labels`
    images plus one ``application_csv``."""
    image_bytes = label_image_bytes()
    files = [("images", (f"label_{i:04d}.png", image_bytes, "image/png")) for i in range(n_labels)]
    files.append(("application_csv", ("application.csv", application_csv_bytes(n_labels), "text/csv")))
    return files
