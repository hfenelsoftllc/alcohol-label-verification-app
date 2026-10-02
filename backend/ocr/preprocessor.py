"""Image pre-processing pipeline for OCR (ISSUE 4.1).

Real-world label photos are often skewed, noisy, and low-contrast — this
hurts OCR accuracy most for the local Tesseract fallback, which has no
built-in image understanding. `maybe_preprocess(image_bytes, quality_score)`
runs a copy of the image through deskew -> denoise -> sharpen -> contrast
before it reaches `ocr.adapter.extract_fields`, using OpenCV's
`getRotationMatrix2D`, `fastNlMeansDenoisingColored`, and `equalizeHist`
(FedRAMP SI-10, Information Input Validation).

Pre-processing is skipped when the image already scores above
`SKIP_QUALITY_THRESHOLD` on `ocr.quality.assess_image_quality`, so an
already-good photo is never degraded. The original image bytes/array are
never modified, and any failure degrades back to the original bytes rather
than raising or rejecting the image.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from ocr.quality import decode_image

logger = logging.getLogger(__name__)

#: Skip pre-processing entirely when assess_image_quality() already scores
#: the image above this — avoids degrading an already-good photo.
SKIP_QUALITY_THRESHOLD = 80.0

#: Rotation estimates below this many degrees aren't worth correcting.
_MIN_SKEW_ANGLE = 0.5

#: fastNlMeansDenoisingColored params, tuned down from OpenCV's defaults
#: (templateWindowSize=7, searchWindowSize=21) so this step -- by far the
#: most expensive part of the pipeline -- leaves comfortable margin under
#: the ~0.5s pre-processing time budget on an 800x800 image (~0.1s vs.
#: ~0.6s+ at the defaults).
_DENOISE_H = 8.0
_DENOISE_H_COLOR = 8.0
_DENOISE_TEMPLATE_WINDOW = 3
_DENOISE_SEARCH_WINDOW = 5

#: Unsharp-mask parameters: sharpened = image * (1 + amount) - blurred * amount.
_SHARPEN_BLUR_SIGMA = 1.0
_SHARPEN_AMOUNT = 1.0

#: Weight given to the equalizeHist result when blending it back with the
#: original luma channel. A full equalizeHist (weight 1.0) over-corrects: on
#: a low-contrast image it can overshoot into an excessive_glare reading, and
#: it stretches whatever low-amplitude sensor noise survives _denoise into
#: visible speckle. This blend still raises a low-contrast image's intensity
#: stddev several-fold (resolving "low_contrast") without either side effect.
_CONTRAST_BLEND_WEIGHT = 0.3


def maybe_preprocess(image_bytes: bytes, quality_score: float) -> bytes:
    """Run `preprocess_image` unless the image already scores well.

    `quality_score` is the score from `ocr.quality.assess_image_quality`,
    computed once by the caller and reused here to avoid a second decode.
    """
    if quality_score > SKIP_QUALITY_THRESHOLD:
        return image_bytes
    return preprocess_image(image_bytes)


def preprocess_image(image_bytes: bytes) -> bytes:
    """Deskew, denoise, sharpen, and contrast-enhance a copy of the image.

    Returns new PNG-encoded bytes. Never modifies `image_bytes` or its
    decoded array, and never raises — any decode/encode/OpenCV failure
    returns `image_bytes` unchanged (FedRAMP SI-10: degrade gracefully,
    never reject an image).
    """
    image = decode_image(image_bytes)
    if image is None or image.size == 0:
        return image_bytes

    try:
        processed = _deskew(image)
        processed = _denoise(processed)
        processed = _sharpen(processed)
        processed = _enhance_contrast(processed)
        ok, buf = cv2.imencode(".png", processed)
    except Exception:
        logger.warning("Image pre-processing failed; using original image.", exc_info=True)
        return image_bytes

    if not ok:
        return image_bytes
    return buf.tobytes()


def _deskew(image: np.ndarray) -> np.ndarray:
    """Rotate a copy of `image` to correct its estimated skew angle."""
    angle = _estimate_skew_angle(image)
    if abs(angle) < _MIN_SKEW_ANGLE:
        return image.copy()

    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _estimate_skew_angle(image: np.ndarray) -> float:
    """Estimate rotation in degrees from the largest contour's bounding rectangle.

    Returns 0.0 if no contour is large enough to represent the label (a tiny
    or fully-uniform image can't meaningfully be deskewed).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
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


def _denoise(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(
        image,
        None,
        h=_DENOISE_H,
        hColor=_DENOISE_H_COLOR,
        templateWindowSize=_DENOISE_TEMPLATE_WINDOW,
        searchWindowSize=_DENOISE_SEARCH_WINDOW,
    )


def _sharpen(image: np.ndarray) -> np.ndarray:
    """Unsharp mask: amplify the difference between `image` and a blurred copy."""
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=_SHARPEN_BLUR_SIGMA)
    return cv2.addWeighted(image, 1 + _SHARPEN_AMOUNT, blurred, -_SHARPEN_AMOUNT, 0)


def _enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Histogram-equalize the luma channel, blended with the original to
    avoid over-enhancement, preserving color balance."""
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y_eq = cv2.equalizeHist(y)
    y = cv2.addWeighted(y_eq, _CONTRAST_BLEND_WEIGHT, y, 1 - _CONTRAST_BLEND_WEIGHT, 0)
    return cv2.cvtColor(cv2.merge((y, cr, cb)), cv2.COLOR_YCrCb2BGR)
