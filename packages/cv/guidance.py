"""Retake guidance generator for evidence quality."""

from __future__ import annotations

from packages.core.vision.quality import ImageQualityMetrics


def retake_guidance(metrics: ImageQualityMetrics) -> list[str]:
    """Return 2–4 tips max, deterministic."""
    tips: list[str] = []
    if metrics.is_low_res:
        tips.append("Move closer; fill the frame with the label/tag.")
    if metrics.is_too_blurry:
        tips.append("Hold steady and tap to focus; avoid motion.")
    if metrics.is_too_dark:
        tips.append("Increase lighting / enable flashlight.")
    if metrics.is_too_glary:
        tips.append("Change angle to reduce glare; avoid direct reflections.")
    tips.append("Center the port label strip and cable tag in the frame.")
    return tips[:4]
