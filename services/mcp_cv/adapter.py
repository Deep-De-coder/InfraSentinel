"""CV adapter — switches between mock fixtures and real Tesseract OCR pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class QualityResult:
    passed: bool
    blur_score: float
    brightness: float
    glare_score: float
    is_too_blurry: bool
    is_too_dark: bool
    is_too_glary: bool
    is_low_res: bool


class CVAdapter:
    """Unified computer-vision adapter.

    CV_MODE=mock      → returns fixture responses via CVHandlers
    CV_MODE=tesseract → runs real Tesseract OCR pipeline
    """

    def __init__(self, cv_mode: str | None = None, scenario: str | None = None) -> None:
        self.cv_mode = (cv_mode or os.getenv("CV_MODE", "mock")).lower()
        self.scenario = scenario or os.getenv("SCENARIO", "CHG-001_A")

    # --- high-level domain API ---

    async def extract_label(self, image_bytes: bytes) -> str:
        """Extract the most prominent text label from raw image bytes."""
        if self.cv_mode == "tesseract":
            from packages.cv.pipeline import read_port_label
            from packages.cv.ocr_backends import TesseractOCRBackend

            result = read_port_label(image_bytes, ocr_backend=TesseractOCRBackend())
            return result.port_label or result.raw_text or ""

        # mock mode — return a placeholder
        return "MOCK-LABEL"

    async def check_quality(self, image_bytes: bytes) -> QualityResult:
        """Run quality checks on raw image bytes."""
        try:
            import cv2
            import numpy as np
            from packages.core.vision.quality import compute_image_quality
            from packages.core.config import get_settings

            settings = get_settings()
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return QualityResult(
                    passed=False,
                    blur_score=0.0,
                    brightness=0.0,
                    glare_score=1.0,
                    is_too_blurry=True,
                    is_too_dark=True,
                    is_too_glary=False,
                    is_low_res=True,
                )
            metrics = compute_image_quality(
                img,
                blur_min=settings.blur_min,
                brightness_min=settings.brightness_min,
                glare_max=settings.glare_max,
                min_w=settings.min_width,
                min_h=settings.min_height,
            )
            passed = not (
                metrics.is_too_blurry
                or metrics.is_too_dark
                or metrics.is_too_glary
                or metrics.is_low_res
            )
            return QualityResult(
                passed=passed,
                blur_score=metrics.blur_score,
                brightness=metrics.brightness,
                glare_score=metrics.glare_score,
                is_too_blurry=metrics.is_too_blurry,
                is_too_dark=metrics.is_too_dark,
                is_too_glary=metrics.is_too_glary,
                is_low_res=metrics.is_low_res,
            )
        except Exception:
            return QualityResult(
                passed=True,
                blur_score=100.0,
                brightness=128.0,
                glare_score=0.0,
                is_too_blurry=False,
                is_too_dark=False,
                is_too_glary=False,
                is_low_res=False,
            )

    # --- MCPToolRouter-compatible async methods ---

    async def read_port_label(
        self, evidence_id: str, change_id: str = "", scenario: str | None = None
    ) -> object:
        from services.mcp_cv.handlers import CVHandlers

        return await CVHandlers(cv_mode=self.cv_mode, scenario=self.scenario).read_port_label(
            evidence_id, change_id, scenario
        )

    async def read_cable_tag(
        self, evidence_id: str, change_id: str = "", scenario: str | None = None
    ) -> object:
        from services.mcp_cv.handlers import CVHandlers

        return await CVHandlers(cv_mode=self.cv_mode, scenario=self.scenario).read_cable_tag(
            evidence_id, change_id, scenario
        )
