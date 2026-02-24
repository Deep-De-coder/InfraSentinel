from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    out = text.strip().upper()
    out = re.sub(r"\s+", " ", out)
    # OCR confusion normalization for label/tag formats.
    out = out.replace("O", "0")
    out = out.replace("I", "1")
    out = out.replace("S", "5")
    return out


def parse_port_label(text: str) -> tuple[str | None, float]:
    normalized = normalize_text(text)
    port_style = re.search(r"\bPORT\s*([0-9]{1,2})\b", normalized)
    p_style = re.search(r"\bP\s*([0-9]{1,2})\b", normalized)
    numeric = re.search(r"\b([0-9]{1,2})\b", normalized)
    alpha = re.search(r"\b([AB])\s*([0-9]{1,2})\b", normalized)

    if alpha:
        idx = int(alpha.group(2))
        if 1 <= idx <= 24:
            return f"{alpha.group(1)}{idx}", 1.0
    for match, score in ((port_style, 0.95), (p_style, 0.92), (numeric, 0.88)):
        if match:
            idx = int(match.group(1))
            if 1 <= idx <= 48:
                return str(idx), score
    return None, 0.35


def parse_cable_tag(text: str) -> tuple[str | None, float]:
    normalized = normalize_text(text)
    strict = re.search(r"\b([A-Z0-9]+-[0-9]{2}-[A-Z0-9]+-[A-Z0-9]+)\b", normalized)
    rack = re.search(r"\b(R[0-9]+-U[0-9]+-PP[0-9]+-[0-9]+)\b", normalized)
    generic = re.search(r"\b([A-Z0-9\-_/]{6,})\b", normalized)
    if strict:
        return strict.group(1), 1.0
    if rack:
        return rack.group(1), 0.95
    if generic:
        return generic.group(1), 0.75
    return None, 0.3
