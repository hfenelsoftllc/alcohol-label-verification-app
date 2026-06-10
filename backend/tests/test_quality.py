"""Tests for image quality assessment (ISSUE 2.2)."""

from __future__ import annotations

import cv2
import numpy as np

from ocr.quality import assess_image_quality


def _encode(image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image)
    assert ok
    return buf.tobytes()


def _checkerboard(size: int = 800, cell: int = 80, square: int = 30, light: int = 200, dark: int = 50) -> np.ndarray:
    """A scattered grid of small dark squares — simulates text on a label."""
    image = np.full((size, size), light, dtype=np.uint8)
    for y in range(cell // 2, size, cell):
        for x in range(cell // 2, size, cell):
            image[y : y + square, x : x + square] = dark
    return image


def test_pristine_image_scores_high():
    report = assess_image_quality(_encode(_checkerboard()))
    assert report.score > 80
    assert report.issues == []


def test_glare_image_scores_mid_range():
    image = _checkerboard()
    image[100:400, 100:600] = 255  # large overexposed patch
    report = assess_image_quality(_encode(image))
    assert 40 <= report.score <= 70
    assert "excessive_glare" in report.issues


def test_very_dark_image_scores_low():
    rng = np.random.default_rng(0)
    image = rng.integers(5, 12, size=(800, 800), dtype=np.uint8)
    report = assess_image_quality(_encode(image))
    assert report.score < 40
    assert "blurry" in report.issues


def test_low_resolution_flagged():
    image = _checkerboard(size=300, cell=30, square=11)
    report = assess_image_quality(_encode(image))
    assert "low_resolution" in report.issues


def test_skewed_image_flagged():
    image = np.full((800, 800), 200, dtype=np.uint8)
    cv2.rectangle(image, (150, 150), (650, 650), 40, -1)
    matrix = cv2.getRotationMatrix2D((400, 400), 15, 1.0)
    image = cv2.warpAffine(image, matrix, (800, 800), borderValue=200)
    report = assess_image_quality(_encode(image))
    assert "skewed_angle" in report.issues


def test_partial_obstruction_flagged():
    image = _checkerboard()
    image[500:750, 100:400] = 5  # large dark blob covering part of the label
    report = assess_image_quality(_encode(image))
    assert "partial_obstruction" in report.issues


def test_unreadable_image_degrades_gracefully():
    report = assess_image_quality(b"this is not an image")
    assert report.score == 0.0
    assert report.issues == ["unreadable"]


def test_score_always_within_bounds():
    for image_bytes in (_encode(_checkerboard()), b"garbage"):
        report = assess_image_quality(image_bytes)
        assert 0.0 <= report.score <= 100.0
