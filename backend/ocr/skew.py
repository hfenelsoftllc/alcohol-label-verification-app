"""Shared skew-estimation/rotation primitives for `ocr.quality` and
`ocr.preprocessor`, which each apply their own no-op threshold and image
format (gray vs. BGR) around these.
"""

from __future__ import annotations

import cv2
import numpy as np


def estimate_angle(gray: np.ndarray) -> float:
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


def rotate(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate `image` (gray or BGR) about its center by `angle` degrees."""
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
