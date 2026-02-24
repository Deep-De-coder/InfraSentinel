from __future__ import annotations

import numpy as np


def crop_region(
    image_bgr: np.ndarray, crop_hint: tuple[int, int, int, int] | None = None
) -> np.ndarray:
    if crop_hint is None:
        return image_bgr
    x, y, w, h = crop_hint
    h_img, w_img = image_bgr.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = max(1, min(w, w_img - x))
    h = max(1, min(h, h_img - y))
    return image_bgr[y : y + h, x : x + w]
