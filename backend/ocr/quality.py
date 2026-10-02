"""Image quality assessment (ISSUE 2.2).

Real-world label photos have glare, skew, blur, and obstructions.
`assess_image_quality(image_bytes)` scores a label photo 0-100 and lists the
issues detected, so the system can communicate quality to the reviewer instead
of silently returning bad results. The system never rejects an image based on
quality alone — it degrades gracefully and reports a lower score (FedRAMP
SI-10, Information Input Validation).

OpenCV is used for pre-processing: denoising (to measure real edge content
without sensor noise), histogram equalization (to make label boundaries
easier to find for skew detection), and deskewing (to correct rotation before
checking for obstructions).
"""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.models import ImageQualityReport

#: Below this width or height (px), an image is flagged "low_resolution".
_MIN_DIMENSION = 600

#: Laplacian variance below this, on a denoised image, is flagged "blurry".
_BLUR_VARIANCE_THRESHOLD = 100.0

#: Pixel-intensity stddev below this indicates a flat/low-contrast capture
#: (stacks with the "blurry" penalty rather than its own issue).
_LOW_CONTRAST_THRESHOLD = 20.0

#: Fraction of near-white (>=250) pixels above this is flagged "excessive_glare".
_GLARE_RATIO_THRESHOLD = 0.05

#: Rotation beyond this many degrees is flagged "skewed_angle".
_SKEW_ANGLE_THRESHOLD = 5.0

#: A connected dark blob covering a fraction of the image in this range looks
#: like something (a finger, a card) partially covering the label — not the
#: whole frame being dark.
_OBSTRUCTION_MIN_RATIO = 0.10
_OBSTRUCTION_MAX_RATIO = 0.60

_PENALTIES = {
    "low_resolution": 15.0,
    "blurry": 35.0,
    "excessive_glare": 35.0,
    "skewed_angle": 15.0,
    "partial_obstruction": 25.0,
}

#: Additional penalty for a flat/low-contrast image, stacked on top of
#: "blurry" when both fire (e.g. a near-black photo).
_LOW_CONTRAST_PENALTY = 35.0


def assess_image_quality(image_bytes: bytes) -> ImageQualityReport:
    """Score a label photo 0-100 and list detected quality issues.

    Never raises. An image that OpenCV cannot decode (the caller has already
    checked it has a recognized image signature) degrades to score 0 with the
    "unreadable" issue rather than being rejected here.
    """
    image = decode_image(image_bytes)
    if image is None or image.size == 0:
        return ImageQualityReport(score=0.0, issues=["unreadable"])

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]

    issues: list[str] = []
    score = 100.0

    if width < _MIN_DIMENSION or height < _MIN_DIMENSION:
        issues.append("low_resolution")
        score -= _PENALTIES["low_resolution"]

    # Denoise before measuring sharpness so sensor noise isn't mistaken for detail.
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    variance = cv2.Laplacian(denoised, cv2.CV_64F).var()
    if variance < _BLUR_VARIANCE_THRESHOLD:
        issues.append("blurry")
        score -= _PENALTIES["blurry"]
    if float(gray.std()) < _LOW_CONTRAST_THRESHOLD:
        score -= _LOW_CONTRAST_PENALTY

    bright_ratio = float(np.mean(gray >= 250))
    if bright_ratio > _GLARE_RATIO_THRESHOLD:
        issues.append("excessive_glare")
        score -= _PENALTIES["excessive_glare"]

    # Contrast-enhance before contour-based checks so low-contrast label edges
    # are easier to separate from the background.
    enhanced = cv2.equalizeHist(denoised)

    angle = _estimate_skew_angle(enhanced)
    if abs(angle) > _SKEW_ANGLE_THRESHOLD:
        issues.append("skewed_angle")
        score -= _PENALTIES["skewed_angle"]

    deskewed = _deskew(enhanced, angle)
    if _has_partial_obstruction(deskewed):
        issues.append("partial_obstruction")
        score -= _PENALTIES["partial_obstruction"]

    return ImageQualityReport(score=max(0.0, min(100.0, score)), issues=issues)


def decode_image(image_bytes: bytes) -> np.ndarray | None:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is not None:
        return image

    # OpenCV's libpng rejects some images (e.g. CRC errors) that Pillow tolerates.
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_image:
            return cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def _estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate rotation in degrees from the largest contour's bounding rectangle.

    Returns 0.0 if no contour is large enough to represent the label (a tiny or
    fully-uniform image can't meaningfully be deskewed).
    """
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    total_area = gray.shape[0] * gray.shape[1]
    if area < 0.01 * total_area or area > 0.98 * total_area:
        return 0.0

    angle = cv2.minAreaRect(largest)[-1]
    if angle < -45:
        angle += 90
    return angle


def _deskew(gray: np.ndarray, angle: float) -> np.ndarray:
    """Rotate the image to correct the estimated skew. A no-op for small angles."""
    if abs(angle) < 0.1:
        return gray
    height, width = gray.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _has_partial_obstruction(gray: np.ndarray) -> bool:
    """True if a large-but-not-whole-frame dark blob suggests part of the label
    is covered (e.g. a finger over the lens), as opposed to the whole image
    being dark."""
    _, dark_mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY_INV)
    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(dark_mask, connectivity=8)
    total_area = gray.shape[0] * gray.shape[1]
    for i in range(1, num_labels):
        ratio = stats[i, cv2.CC_STAT_AREA] / total_area
        if _OBSTRUCTION_MIN_RATIO < ratio < _OBSTRUCTION_MAX_RATIO:
            return True
    return False
