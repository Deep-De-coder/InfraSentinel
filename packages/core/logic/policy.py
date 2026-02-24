"""Policy constants and helpers."""

from __future__ import annotations

DEFAULT_MIN_CONF = 0.75

DEFAULT_RETAKE_GUIDANCE = [
    "Move closer and fill the frame with the label",
    "Reduce glare / change angle",
    "Tap to focus / hold steady",
    "Increase lighting",
]


def retake_guidance_from_quality(quality: object | None = None) -> list[str]:
    """Return actionable retake guidance. Quality can inform which tips to include."""
    return list(DEFAULT_RETAKE_GUIDANCE)


def must_block_on_low_confidence(confidence: float, min_conf: float = DEFAULT_MIN_CONF) -> bool:
    """NEVER GREEN under low confidence."""
    return confidence < min_conf
