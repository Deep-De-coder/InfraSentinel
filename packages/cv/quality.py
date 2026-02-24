from __future__ import annotations

import cv2
import numpy as np

from packages.cv.schema import QualityMetrics

BLUR_THRESHOLD = 90.0
BRIGHTNESS_THRESHOLD = 55.0
GLARE_THRESHOLD = 0.08


def compute_quality_metrics(image_bgr: np.ndarray) -> QualityMetrics:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    glare_score = float((gray > 245).sum() / gray.size)
    return QualityMetrics(
        blur_score=blur_score,
        brightness=brightness,
        glare_score=glare_score,
        too_dark=brightness < BRIGHTNESS_THRESHOLD,
        too_blurry=blur_score < BLUR_THRESHOLD,
    )


def quality_penalty(quality: QualityMetrics) -> float:
    penalty = 1.0
    if quality.too_blurry:
        penalty *= 0.65
    if quality.too_dark:
        penalty *= 0.75
    if quality.glare_score > GLARE_THRESHOLD:
        penalty *= 0.75
    return max(0.2, min(1.0, penalty))


def retake_guidance(quality: QualityMetrics) -> list[str]:
    tips: list[str] = []
    if quality.too_blurry:
        tips.append("Tap to focus / hold steady")
    if quality.glare_score > GLARE_THRESHOLD:
        tips.append("Reduce glare / change angle")
    if quality.too_dark:
        tips.append("Increase lighting")
    if not tips:
        tips.append("Move closer and fill the frame with the label")
    elif "Move closer and fill the frame with the label" not in tips:
        tips.append("Move closer and fill the frame with the label")
    return tips
