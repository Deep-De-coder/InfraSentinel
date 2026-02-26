"""Generate sample images for quality gate tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> None:
    out_dir = _repo_root() / "samples" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)

    w, h = 1280, 720
    base = np.zeros((h, w, 3), dtype=np.uint8)
    base[:] = (180, 180, 180)
    cv2.putText(base, "PORT 24", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3)
    cv2.putText(base, "MDF-01-R12-P24", (350, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)

    evid_good = base.copy()
    cv2.imwrite(str(out_dir / "evid-good.jpg"), evid_good)

    evid_blurry = cv2.GaussianBlur(base, (25, 25), 5.0)
    cv2.imwrite(str(out_dir / "evid-blurry.jpg"), evid_blurry)

    evid_dark = cv2.convertScaleAbs(base, alpha=0.3, beta=-80)
    cv2.imwrite(str(out_dir / "evid-dark.jpg"), evid_dark)

    evid_glare = base.copy()
    # Large bright patch: >8% of pixels above 245 to fail glare gate
    cv2.rectangle(evid_glare, (200, 100), (600, 500), (255, 255, 255), -1)
    cv2.imwrite(str(out_dir / "evid-glare.jpg"), evid_glare)

    print(f"Generated 4 images in {out_dir}")


if __name__ == "__main__":
    main()
