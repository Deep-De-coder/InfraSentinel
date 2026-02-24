from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

from packages.cv.schema import OCRSpan
from services.common import load_sample_json


class OCRBackend(ABC):
    @abstractmethod
    def read_text(self, image_bgr: np.ndarray, evidence_id: str | None = None) -> list[OCRSpan]:
        raise NotImplementedError


class MockOCRBackend(OCRBackend):
    def __init__(self) -> None:
        self.fixtures = load_sample_json("cv_outputs.json")

    def read_text(self, image_bgr: np.ndarray, evidence_id: str | None = None) -> list[OCRSpan]:
        key = evidence_id or "default"
        item = self.fixtures.get(key, self.fixtures["default"])
        raw_text = item.get("raw_text") or f'{item.get("port_label", "")} {item.get("cable_tag", "")}'.strip()
        return [OCRSpan(text=raw_text, conf=float(item.get("ocr_conf", 0.95)), bbox=None)]


class TesseractOCRBackend(OCRBackend):
    def __init__(self) -> None:
        try:
            import pytesseract as _pytesseract
        except ImportError as exc:  # pragma: no cover - optional path
            raise RuntimeError(
                "pytesseract is not installed. Install with `uv add pytesseract` and ensure "
                "the tesseract binary is installed and available in PATH."
            ) from exc
        self.pytesseract = _pytesseract

    def read_text(self, image_bgr: np.ndarray, evidence_id: str | None = None) -> list[OCRSpan]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        data = self.pytesseract.image_to_data(gray, output_type=self.pytesseract.Output.DICT)
        spans: list[OCRSpan] = []
        for i, txt in enumerate(data.get("text", [])):
            text = (txt or "").strip()
            if not text:
                continue
            conf_raw = float(data["conf"][i]) if i < len(data["conf"]) else 0.0
            conf = max(0.0, min(1.0, conf_raw / 100.0))
            bbox = (
                int(data["left"][i]),
                int(data["top"][i]),
                int(data["width"][i]),
                int(data["height"][i]),
            )
            spans.append(OCRSpan(text=text, conf=conf, bbox=bbox))
        if spans:
            return spans
        return [OCRSpan(text="", conf=0.0, bbox=None)]


def resolve_local_image_path(evidence_id: str) -> Path | None:
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "samples" / "images" / f"{evidence_id}.png",
        root / "samples" / "images" / f"{evidence_id}.jpg",
        root / ".data" / "evidence",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
        if candidate.is_dir():
            matches = sorted(candidate.glob(f"{evidence_id}_*"))
            if matches:
                return matches[-1]
    return None
