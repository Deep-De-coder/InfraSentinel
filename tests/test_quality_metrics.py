"""Unit tests for image quality metrics."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from packages.core.vision.quality import (
    ImageQualityMetrics,
    compute_image_quality,
    resolution_ok,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_good_image_passes() -> None:
    """Sharp, bright image at sufficient resolution passes all gates."""
    img_path = _repo_root() / "samples" / "images" / "evid-good.jpg"
    if not img_path.exists():
        pytest.skip("Run scripts/gen_sample_images.py first")
    img = cv2.imread(str(img_path))
    assert img is not None
    metrics = compute_image_quality(img)
    assert not metrics.is_too_blurry
    assert not metrics.is_too_dark
    assert not metrics.is_too_glary
    assert not metrics.is_low_res


def test_blurry_image_fails() -> None:
    """Blurry image fails blur gate."""
    img_path = _repo_root() / "samples" / "images" / "evid-blurry.jpg"
    if not img_path.exists():
        pytest.skip("Run scripts/gen_sample_images.py first")
    img = cv2.imread(str(img_path))
    assert img is not None
    metrics = compute_image_quality(img)
    assert metrics.is_too_blurry


def test_dark_image_fails() -> None:
    """Dark image fails brightness gate."""
    img_path = _repo_root() / "samples" / "images" / "evid-dark.jpg"
    if not img_path.exists():
        pytest.skip("Run scripts/gen_sample_images.py first")
    img = cv2.imread(str(img_path))
    assert img is not None
    metrics = compute_image_quality(img)
    assert metrics.is_too_dark


def test_glare_image_fails() -> None:
    """Image with glare fails glare gate."""
    img_path = _repo_root() / "samples" / "images" / "evid-glare.jpg"
    if not img_path.exists():
        pytest.skip("Run scripts/gen_sample_images.py first")
    img = cv2.imread(str(img_path))
    assert img is not None
    metrics = compute_image_quality(img)
    assert metrics.is_too_glary


def test_resolution_ok() -> None:
    """Resolution check respects min width/height."""
    small = np.zeros((500, 700, 3), dtype=np.uint8)
    assert not resolution_ok(small, min_w=800, min_h=600)
    large = np.zeros((720, 1280, 3), dtype=np.uint8)
    assert resolution_ok(large, min_w=800, min_h=600)


def test_low_res_flagged() -> None:
    """Small image is flagged as low_res."""
    small = np.zeros((400, 500, 3), dtype=np.uint8)
    cv2.putText(small, "X", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    metrics = compute_image_quality(small, min_w=800, min_h=600)
    assert metrics.is_low_res
