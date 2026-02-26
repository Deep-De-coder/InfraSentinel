"""Evidence retrieval for quality gate and CV."""

from __future__ import annotations

from pathlib import Path

from packages.core.fixtures.loaders import resolve_evidence as _resolve_path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_evidence_bytes(
    evidence_id: str,
    change_id: str = "",
    local_evidence_dir: Path | None = None,
) -> bytes | None:
    """Resolve evidence_id to bytes. Fixture path first, then local storage."""
    path = _resolve_path(evidence_id, change_id)
    if path and path.exists():
        return path.read_bytes()
    if local_evidence_dir and local_evidence_dir.exists():
        matches = sorted(local_evidence_dir.glob(f"{evidence_id}_*"))
        if not matches:
            matches = sorted(local_evidence_dir.glob(f"{evidence_id}*"))
        if matches:
            return matches[-1].read_bytes()
    img_dir = _repo_root() / "samples" / "images"
    for ext in (".png", ".jpg", ".jpeg"):
        p = img_dir / f"{evidence_id}{ext}"
        if p.exists():
            return p.read_bytes()
    return None
