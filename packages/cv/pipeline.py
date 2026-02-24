from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from packages.cv.crop import crop_region
from packages.cv.ocr_backends import OCRBackend
from packages.cv.parsing import parse_cable_tag, parse_port_label
from packages.cv.quality import compute_quality_metrics, quality_penalty, retake_guidance
from packages.cv.schema import CableTagResult, PortLabelResult

PORT_ACCEPT_CONF = 0.75
TAG_ACCEPT_CONF = 0.75


def _load_image(image_path_or_bytes: str | bytes | bytearray | np.ndarray) -> np.ndarray:
    if isinstance(image_path_or_bytes, np.ndarray):
        return image_path_or_bytes
    if isinstance(image_path_or_bytes, (bytes, bytearray)):
        arr = np.frombuffer(image_path_or_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(str(Path(image_path_or_bytes)))
    if img is None:
        return np.zeros((128, 256, 3), dtype=np.uint8)
    return img


def _join_spans(spans: list) -> tuple[str, float]:
    if not spans:
        return "", 0.0
    raw = " ".join([span.text for span in spans]).strip()
    ocr_conf = sum(span.conf for span in spans) / len(spans)
    return raw, float(max(0.0, min(1.0, ocr_conf)))


def read_port_label(
    image_path_or_bytes: str | bytes | bytearray | np.ndarray,
    ocr_backend: OCRBackend,
    evidence_id: str | None = None,
    crop_hint: tuple[int, int, int, int] | None = None,
) -> PortLabelResult:
    image = _load_image(image_path_or_bytes)
    quality = compute_quality_metrics(image)
    cropped = crop_region(image, crop_hint=crop_hint)
    spans = ocr_backend.read_text(cropped, evidence_id=evidence_id)
    raw_text, ocr_conf = _join_spans(spans)
    port_label, parse_conf = parse_port_label(raw_text)
    final_conf = max(0.0, min(1.0, ocr_conf * parse_conf * quality_penalty(quality)))
    guidance = []
    if not port_label or final_conf < PORT_ACCEPT_CONF:
        guidance = retake_guidance(quality)
    panel_id = "PANEL-A" if port_label else None
    return PortLabelResult(
        panel_id=panel_id,
        port_label=port_label,
        confidence=final_conf,
        quality=quality,
        retake_guidance=guidance,
        raw_text=raw_text,
    )


def read_cable_tag(
    image_path_or_bytes: str | bytes | bytearray | np.ndarray,
    ocr_backend: OCRBackend,
    evidence_id: str | None = None,
    crop_hint: tuple[int, int, int, int] | None = None,
) -> CableTagResult:
    image = _load_image(image_path_or_bytes)
    quality = compute_quality_metrics(image)
    cropped = crop_region(image, crop_hint=crop_hint)
    spans = ocr_backend.read_text(cropped, evidence_id=evidence_id)
    raw_text, ocr_conf = _join_spans(spans)
    cable_tag, parse_conf = parse_cable_tag(raw_text)
    final_conf = max(0.0, min(1.0, ocr_conf * parse_conf * quality_penalty(quality)))
    guidance = []
    if not cable_tag or final_conf < TAG_ACCEPT_CONF:
        guidance = retake_guidance(quality)
    return CableTagResult(
        cable_tag=cable_tag,
        confidence=final_conf,
        quality=quality,
        retake_guidance=guidance,
        raw_text=raw_text,
    )
