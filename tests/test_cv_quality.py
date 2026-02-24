import cv2
import numpy as np

from packages.cv.quality import compute_quality_metrics


def test_blur_metric_separates_sharp_and_blurry() -> None:
    sharp = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.putText(sharp, "PORT 24", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    blurry = cv2.GaussianBlur(sharp, (15, 15), sigmaX=4.0)

    sharp_q = compute_quality_metrics(sharp)
    blur_q = compute_quality_metrics(blurry)
    assert sharp_q.blur_score > blur_q.blur_score


def test_dark_image_flagged() -> None:
    dark = np.zeros((120, 160, 3), dtype=np.uint8)
    q = compute_quality_metrics(dark)
    assert q.too_dark is True
