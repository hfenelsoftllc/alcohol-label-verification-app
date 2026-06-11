"""A/B test: OpenCV pre-processing pipeline vs. raw image quality (ISSUE 4.1).

This repo has no real-world label photos to test against, so this script
generates 20 synthetic "label photo" samples — a checkerboard pattern
(simulating printed text on a label, as in `tests/test_preprocessor.py`)
rotated by a skew angle and degraded with Gaussian noise, approximating the
skew + noise + reduced-contrast profile of a typical phone photo.

For each sample, `ocr.quality.assess_image_quality` scores the image 0-100
before and after `ocr.preprocessor.preprocess_image` (deskew -> denoise ->
sharpen -> contrast). Results are written to
`docs/fedramp/PREPROCESSING-AB-TEST.md`, with a few before/after sample
images saved to `docs/fedramp/assets/preprocessing-ab-test/` as a visual
showcase (FedRAMP SI-10).

Run from the `backend/` directory:

    python scripts/preprocessing_ab_test.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ocr.preprocessor import preprocess_image  # noqa: E402
from ocr.quality import assess_image_quality, decode_image  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS_DIR = _REPO_ROOT / "docs" / "fedramp"
_ASSETS_DIR = _DOCS_DIR / "assets" / "preprocessing-ab-test"
_REPORT_PATH = _DOCS_DIR / "PREPROCESSING-AB-TEST.md"

#: Sample count and skew-angle range, evenly spaced across the samples.
_SAMPLE_COUNT = 20
_MIN_ANGLE = 3.0
_MAX_ANGLE = 22.0

#: Gaussian noise standard deviation applied to every sample.
_NOISE_STD = 10.0

#: 1-based sample indices to save before/after images for, as a visual showcase.
_SHOWCASE_SAMPLES = (1, 10, 20)


def _checkerboard(size: int = 800, cell: int = 80, square: int = 30, light: int = 200, dark: int = 50) -> np.ndarray:
    """A scattered grid of small dark squares — simulates text on a label."""
    image = np.full((size, size), light, dtype=np.uint8)
    for y in range(cell // 2, size, cell):
        for x in range(cell // 2, size, cell):
            image[y : y + square, x : x + square] = dark
    return image


def _degraded_label(angle: float, noise_std: float, seed: int) -> np.ndarray:
    """A checkerboard, rotated and with added Gaussian noise — simulates a
    real-world phone photo: skewed, slightly noisy, lower contrast."""
    image = _checkerboard()
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, noise_std, image.shape)
    noisy = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    matrix = cv2.getRotationMatrix2D((400, 400), angle, 1.0)
    rotated = cv2.warpAffine(noisy, matrix, (800, 800), borderValue=200)
    return cv2.cvtColor(rotated, cv2.COLOR_GRAY2BGR)


def _encode(image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image)
    assert ok
    return buf.tobytes()


def main() -> None:
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Warm up OpenCV's thread pool / SIMD dispatch so the first timed sample
    # isn't penalized by one-time process-startup overhead -- a long-running
    # API server pays this cost once, not per image.
    preprocess_image(_encode(_degraded_label(angle=10.0, noise_std=_NOISE_STD, seed=0)))

    rows = []
    for i in range(1, _SAMPLE_COUNT + 1):
        angle = _MIN_ANGLE + (i - 1) * (_MAX_ANGLE - _MIN_ANGLE) / (_SAMPLE_COUNT - 1)
        before_bytes = _encode(_degraded_label(angle=angle, noise_std=_NOISE_STD, seed=i))

        before = assess_image_quality(before_bytes)

        start = time.perf_counter()
        after_bytes = preprocess_image(before_bytes)
        elapsed = time.perf_counter() - start

        after = assess_image_quality(after_bytes)

        rows.append(
            {
                "sample": i,
                "angle": angle,
                "before_score": before.score,
                "before_issues": before.issues,
                "after_score": after.score,
                "after_issues": after.issues,
                "delta": after.score - before.score,
                "elapsed": elapsed,
            }
        )

        if i in _SHOWCASE_SAMPLES:
            cv2.imwrite(str(_ASSETS_DIR / f"sample-{i:02d}-before.png"), decode_image(before_bytes))
            cv2.imwrite(str(_ASSETS_DIR / f"sample-{i:02d}-after.png"), decode_image(after_bytes))

    _write_report(rows)
    print(f"Wrote {_REPORT_PATH}")
    print(f"Wrote {len(_SHOWCASE_SAMPLES) * 2} showcase images to {_ASSETS_DIR}")


def _format_issues(issues: list[str]) -> str:
    return ", ".join(issues) if issues else "none"


def _write_report(rows: list[dict]) -> None:
    deltas = [r["delta"] for r in rows]
    elapsed_times = [r["elapsed"] for r in rows]
    improved = sum(1 for d in deltas if d > 0)
    avg_before = sum(r["before_score"] for r in rows) / len(rows)
    avg_after = sum(r["after_score"] for r in rows) / len(rows)
    avg_delta = sum(deltas) / len(deltas)
    avg_elapsed = sum(elapsed_times) / len(elapsed_times)
    max_elapsed = max(elapsed_times)

    lines: list[str] = []
    lines.append("# OpenCV Pre-Processing A/B Test (ISSUE 4.1)")
    lines.append("")
    lines.append("**FedRAMP Control:** SI-10 (Information Input Validation)")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "This repo has no real-world label photos to test against, so this "
        "report uses 20 synthetic \"label photo\" samples generated by "
        "[`backend/scripts/preprocessing_ab_test.py`](../../backend/scripts/preprocessing_ab_test.py): "
        "a checkerboard pattern (simulating printed text on a label) rotated "
        f"by a skew angle ({_MIN_ANGLE:.0f}°–{_MAX_ANGLE:.0f}°, evenly spaced across the "
        f"20 samples) with Gaussian noise added (σ={_NOISE_STD:.0f}), "
        "approximating the skew + noise + reduced-contrast profile of a "
        "typical phone photo."
    )
    lines.append("")
    lines.append(
        "For each sample, [`ocr.quality.assess_image_quality`](../../backend/ocr/quality.py) "
        "scores the image 0-100 before and after "
        "[`ocr.preprocessor.preprocess_image`](../../backend/ocr/preprocessor.py) "
        "(deskew -> denoise -> sharpen -> contrast, via OpenCV's "
        "`getRotationMatrix2D`, `fastNlMeansDenoisingColored`, and "
        "`equalizeHist`). The same scenario runs as a fast regression check in "
        "[`backend/tests/test_preprocessor.py::test_preprocessing_improves_quality_score_on_degraded_images`]"
        "(../../backend/tests/test_preprocessor.py)."
    )
    lines.append("")
    lines.append("To regenerate this report and the sample images:")
    lines.append("")
    lines.append("```")
    lines.append("cd backend")
    lines.append("python scripts/preprocessing_ab_test.py")
    lines.append("```")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Samples | {len(rows)} |")
    lines.append(f"| Average score before | {avg_before:.1f} |")
    lines.append(f"| Average score after | {avg_after:.1f} |")
    lines.append(f"| Average improvement (Δ score) | {avg_delta:+.1f} |")
    lines.append(f"| Samples improved (Δ score > 0) | {improved} / {len(rows)} |")
    lines.append(f"| Average pre-processing time | {avg_elapsed:.3f}s |")
    lines.append(f"| Max pre-processing time | {max_elapsed:.3f}s (budget: ≤ 0.5s, ISSUE 4.1 AC) |")
    lines.append("")
    lines.append(
        "(Timings exclude one untimed warm-up call that absorbs OpenCV's "
        "one-time thread-pool/SIMD-dispatch initialization -- a cost a "
        "long-running API server pays once at startup, not per image.)"
    )
    lines.append("")
    lines.append("## Showcase")
    lines.append("")
    lines.append(
        "Before/after images for a low-skew, median-skew, and high-skew "
        "sample (full results for all 20 samples below)."
    )
    lines.append("")
    for i in _SHOWCASE_SAMPLES:
        row = next(r for r in rows if r["sample"] == i)
        lines.append(f"### Sample {i} — skew {row['angle']:.1f}°")
        lines.append("")
        lines.append("| Before | After |")
        lines.append("|---|---|")
        lines.append(
            f"| ![Sample {i} before](assets/preprocessing-ab-test/sample-{i:02d}-before.png) "
            f"| ![Sample {i} after](assets/preprocessing-ab-test/sample-{i:02d}-after.png) |"
        )
        lines.append(
            f"| Score {row['before_score']:.1f} — {_format_issues(row['before_issues'])} "
            f"| Score {row['after_score']:.1f} — {_format_issues(row['after_issues'])} |"
        )
        lines.append("")
    lines.append("## Full Results")
    lines.append("")
    lines.append("| Sample | Skew angle | Score before | Issues before | Score after | Issues after | Δ score | Time (s) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['sample']} | {r['angle']:.1f}° "
            f"| {r['before_score']:.1f} | {_format_issues(r['before_issues'])} "
            f"| {r['after_score']:.1f} | {_format_issues(r['after_issues'])} "
            f"| {r['delta']:+.1f} | {r['elapsed']:.3f} |"
        )
    lines.append("")

    _REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
