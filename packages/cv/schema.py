from __future__ import annotations

from pydantic import BaseModel, Field


class OCRSpan(BaseModel):
    text: str
    conf: float = Field(ge=0.0, le=1.0)
    bbox: tuple[int, int, int, int] | None = None


class QualityMetrics(BaseModel):
    blur_score: float
    brightness: float
    glare_score: float
    too_dark: bool
    too_blurry: bool


class PortLabelResult(BaseModel):
    panel_id: str | None = None
    port_label: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    quality: QualityMetrics
    retake_guidance: list[str] = Field(default_factory=list)
    raw_text: str


class CableTagResult(BaseModel):
    cable_tag: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    quality: QualityMetrics
    retake_guidance: list[str] = Field(default_factory=list)
    raw_text: str
