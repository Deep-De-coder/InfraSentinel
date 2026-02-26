"""Image quality metrics for evidence gate."""

from __future__ import annotations

import cv2
import numpy as np

from pydantic import BaseModel


class ImageQualityMetrics(BaseModel):
    blur_score: float
    brightness: float
    glare_score: float
    width: int
    height: int
    is_too_blurry: bool
    is_too_dark: bool
    is_too_glary: bool
    is_low_res: bool


def blur_score(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def brightness(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(gray.mean())


def glare_score(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float((gray > 245).sum() / gray.size)


def resolution_ok(img: np.ndarray, min_w: int = 800, min_h: int = 600) -> bool:
    h, w = img.shape[:2]
    return w >= min_w and h >= min_h


def compute_image_quality(
    img: np.ndarray,
    blur_min: float = 120.0,
    brightness_min: float = 60.0,
    glare_max: float = 0.08,
    min_w: int = 800,
    min_h: int = 600,
) -> ImageQualityMetrics:
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    bright = float(gray.mean())
    glare = float((gray > 245).sum() / gray.size)
    h, w = img.shape[:2]
    return ImageQualityMetrics(
        blur_score=blur,
        brightness=bright,
        glare_score=glare,
        width=w,
        height=h,
        is_too_blurry=blur < blur_min,
        is_too_dark=bright < brightness_min,
        is_too_glary=glare > glare_max,
        is_low_res=w < min_w or h < min_h,
    )
