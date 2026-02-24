"""CV MCP handlers with scenario-aware fixture support."""

from __future__ import annotations

import os
from pathlib import Path

from packages.cv.ocr_backends import OCRBackend
from packages.cv.ocr_backends import MockOCRBackend, TesseractOCRBackend, resolve_local_image_path
from packages.cv.pipeline import read_cable_tag, read_port_label
from packages.cv.schema import CableTagResult, PortLabelResult, QualityMetrics
from packages.core.fixtures.loaders import load_cv_outputs, resolve_evidence


class CVHandlers:
    def __init__(self, cv_mode: str | None = None, scenario: str | None = None):
        self.cv_mode = (cv_mode or os.getenv("CV_MODE", "mock")).lower()
        self.scenario = scenario or os.getenv("SCENARIO", "CHG-001_A")
        self.ocr_backend = self._build_backend()

    def _build_backend(self) -> OCRBackend:
        if self.cv_mode == "tesseract":
            return TesseractOCRBackend()
        return MockOCRBackend()

    def _resolve_image(self, evidence_id: str, change_id: str = "") -> str | bytes:
        path = resolve_evidence(evidence_id, change_id)
        if path:
            return str(path)
        path = resolve_local_image_path(evidence_id)
        if path:
            return str(path)
        fallback = Path(__file__).resolve().parents[2] / "samples" / "images" / "default.png"
        return str(fallback)

    def _get_fixture_outputs(self, evidence_id: str, scenario_override: str | None = None) -> dict | None:
        """In mock mode with scenario, return fixture data for evidence_id."""
        scenario = scenario_override or self.scenario
        try:
            data = load_cv_outputs(scenario)
            return data.get(evidence_id, data.get("default"))
        except Exception:
            return None

    async def read_port_label(
        self, evidence_id: str, change_id: str = "", scenario: str | None = None
    ) -> PortLabelResult:
        fixture = self._get_fixture_outputs(evidence_id, scenario)
        if fixture is not None:
            quality = QualityMetrics(
                blur_score=100.0,
                brightness=128.0,
                glare_score=0.0,
                too_dark=False,
                too_blurry=False,
            )
            panel_id = fixture.get("panel_id")
            port_label = fixture.get("port_label")
            conf = float(fixture.get("port_confidence", 0.5))
            guidance = [] if (port_label and conf >= 0.75) else ["Move closer and fill the frame with the label"]
            return PortLabelResult(
                panel_id=str(panel_id) if panel_id else None,
                port_label=str(port_label) if port_label else None,
                confidence=conf,
                quality=quality,
                retake_guidance=guidance,
                raw_text=fixture.get("raw_text", str(port_label or "")),
            )
        image = self._resolve_image(evidence_id, change_id)
        return read_port_label(image, ocr_backend=self.ocr_backend, evidence_id=evidence_id)

    async def read_cable_tag(
        self, evidence_id: str, change_id: str = "", scenario: str | None = None
    ) -> CableTagResult:
        fixture = self._get_fixture_outputs(evidence_id, scenario)
        if fixture is not None:
            quality = QualityMetrics(
                blur_score=100.0,
                brightness=128.0,
                glare_score=0.0,
                too_dark=False,
                too_blurry=False,
            )
            cable_tag = fixture.get("cable_tag")
            conf = float(fixture.get("cable_confidence", 0.5))
            guidance = [] if (cable_tag and conf >= 0.75) else ["Move closer and fill the frame with the label"]
            return CableTagResult(
                cable_tag=str(cable_tag) if cable_tag else None,
                confidence=conf,
                quality=quality,
                retake_guidance=guidance,
                raw_text=fixture.get("raw_text", str(cable_tag or "")),
            )
        image = self._resolve_image(evidence_id, change_id)
        return read_cable_tag(image, ocr_backend=self.ocr_backend, evidence_id=evidence_id)
