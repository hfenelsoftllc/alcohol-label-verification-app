"""Tests for the OpenCV image pre-processing pipeline (ISSUE 4.1)."""

from __future__ import annotations

import time

import cv2
import numpy as np

from ocr import preprocessor
from ocr.preprocessor import maybe_preprocess, preprocess_image
from ocr.quality import assess_image_quality, decode_image


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


def _degraded_label(angle: float = 12.0, noise_std: float = 15.0, seed: int = 0) -> np.ndarray:
    """A checkerboard, rotated and with added Gaussian noise — simulates a
    real-world phone photo: skewed, slightly noisy, lower contrast."""
    image = _checkerboard()
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, noise_std, image.shape)
    noisy = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    matrix = cv2.getRotationMatrix2D((400, 400), angle, 1.0)
    return cv2.warpAffine(noisy, matrix, (800, 800), borderValue=200)


def test_skip_threshold_returns_original_bytes_unchanged():
    """High-quality images bypass the pipeline entirely (avoid degrading good photos)."""
    image_bytes = _encode(_checkerboard())

    assert maybe_preprocess(image_bytes, quality_score=85.0) is image_bytes


def test_below_threshold_runs_pipeline_and_changes_bytes():
    image_bytes = _encode(_degraded_label())

    processed = maybe_preprocess(image_bytes, quality_score=50.0)

    assert processed != image_bytes
    assert decode_image(processed) is not None


def test_threshold_boundary_is_exclusive():
    image_bytes = _encode(_degraded_label())

    # Exactly at the threshold -> still runs the pipeline (not skipped).
    assert maybe_preprocess(image_bytes, quality_score=preprocessor.SKIP_QUALITY_THRESHOLD) != image_bytes
    # Just above the threshold -> skipped.
    assert maybe_preprocess(image_bytes, quality_score=preprocessor.SKIP_QUALITY_THRESHOLD + 0.01) is image_bytes


def test_preprocess_preserves_dimensions_and_channels():
    original = _degraded_label()

    processed = decode_image(preprocess_image(_encode(original)))

    assert processed is not None
    assert processed.shape[:2] == original.shape[:2]
    assert processed.shape[2] == 3


def test_preprocess_handles_undecodable_image_gracefully():
    garbage = b"this is not an image"

    assert preprocess_image(garbage) == garbage
    assert maybe_preprocess(garbage, quality_score=0.0) == garbage


def test_deskew_does_not_mutate_input_array():
    image = cv2.cvtColor(_checkerboard(), cv2.COLOR_GRAY2BGR)
    matrix = cv2.getRotationMatrix2D((400, 400), 10, 1.0)
    skewed = cv2.warpAffine(image, matrix, (800, 800), borderValue=(200, 200, 200))
    original = skewed.copy()

    preprocessor._deskew(skewed)

    assert np.array_equal(skewed, original)


def test_estimate_skew_angle_detects_rotation():
    image = np.full((800, 800), 200, dtype=np.uint8)
    cv2.rectangle(image, (150, 150), (650, 650), 40, -1)
    matrix = cv2.getRotationMatrix2D((400, 400), 15, 1.0)
    rotated = cv2.warpAffine(image, matrix, (800, 800), borderValue=200)

    angle = preprocessor._estimate_skew_angle(cv2.cvtColor(rotated, cv2.COLOR_GRAY2BGR))

    assert abs(angle) > 5.0


def test_preprocess_completes_within_time_budget():
    """ISSUE 4.1 AC: pre-processing adds <=0.5s to total processing time."""
    image_bytes = _encode(_degraded_label())

    start = time.perf_counter()
    preprocess_image(image_bytes)
    elapsed = time.perf_counter() - start

    assert elapsed <= 0.5


def test_preprocessing_improves_quality_score_on_degraded_images():
    """A/B regression check: pre-processing should, on average, raise the
    quality score of degraded label photos (full 20-sample report in
    docs/fedramp/PREPROCESSING-AB-TEST.md).

    Uses noise_std=10.0, matching the A/B script: at higher noise levels,
    _estimate_skew_angle can fail to find a contour on the noisy "before"
    image but succeed once preprocessing has cleaned it up, which flags a
    skew on "after" that "before" never reported and masks the improvement
    being tested here.
    """
    deltas = []
    for seed in range(5):
        for angle in (8.0, 15.0):
            image_bytes = _encode(_degraded_label(angle=angle, noise_std=10.0, seed=seed))
            before = assess_image_quality(image_bytes).score
            after = assess_image_quality(preprocess_image(image_bytes)).score
            deltas.append(after - before)

    assert sum(deltas) / len(deltas) > 0
