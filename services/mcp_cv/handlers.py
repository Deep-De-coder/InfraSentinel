from __future__ import annotations

import os
from pathlib import Path

from packages.cv.ocr_backends import OCRBackend
from packages.cv.ocr_backends import MockOCRBackend, TesseractOCRBackend, resolve_local_image_path
from packages.cv.pipeline import read_cable_tag, read_port_label
from packages.cv.schema import CableTagResult, PortLabelResult


class CVHandlers:
    def __init__(self, cv_mode: str | None = None):
        self.cv_mode = (cv_mode or os.getenv("CV_MODE", "mock")).lower()
        self.ocr_backend = self._build_backend()

    def _build_backend(self) -> OCRBackend:
        if self.cv_mode == "tesseract":
            return TesseractOCRBackend()
        return MockOCRBackend()

    def _resolve_image(self, evidence_id: str) -> str | bytes:
        path = resolve_local_image_path(evidence_id)
        if path:
            return str(path)
        fallback = Path(__file__).resolve().parents[2] / "samples" / "images" / "default.png"
        return str(fallback)

    async def read_port_label(self, evidence_id: str) -> PortLabelResult:
        image = self._resolve_image(evidence_id)
        return read_port_label(image, ocr_backend=self.ocr_backend, evidence_id=evidence_id)

    async def read_cable_tag(self, evidence_id: str) -> CableTagResult:
        image = self._resolve_image(evidence_id)
        return read_cable_tag(image, ocr_backend=self.ocr_backend, evidence_id=evidence_id)
