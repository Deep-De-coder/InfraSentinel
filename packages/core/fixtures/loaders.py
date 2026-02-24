"""Fixture loaders for scenario-based mock mode."""

from __future__ import annotations

import json
from pathlib import Path

from packages.core.models.change import ChangeRequest
from packages.core.models.steps import (
    EvidenceKind,
    EvidenceRequirement,
    StepDefinition,
    StepType,
    VerificationRequirement,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_change(change_id: str) -> ChangeRequest:
    """Load ChangeRequest from scenario change_request.json."""
    base = _repo_root() / "samples" / "scenarios" / change_id
    path = base / "change_request.json"
    if not path.exists():
        base = _repo_root() / "samples" / "scenarios" / "CHG-001"
        path = base / "change_request.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if "change_id" not in data:
        data["change_id"] = change_id
    return _parse_change_request(data)


def _parse_change_request(data: dict) -> ChangeRequest:
    steps = []
    for s in data.get("steps", []):
        ev = s.get("evidence")
        ev_req = EvidenceRequirement(kind=EvidenceKind(ev["kind"]), count=ev["count"]) if ev else None
        ver = s.get("verify")
        ver_req = (
            VerificationRequirement(
                requires_port_label=ver.get("requires_port_label", False),
                requires_cable_tag=ver.get("requires_cable_tag", False),
                min_confidence=ver.get("min_confidence", 0.75),
            )
            if ver
            else None
        )
        app = s.get("approval")
        from packages.core.models.steps import ApprovalGate
        app_gate = ApprovalGate(required=app.get("required", False), on_blocked=app.get("on_blocked", True)) if app else None
        steps.append(
            StepDefinition(
                step_id=s["step_id"],
                description=s["description"],
                step_type=StepType(s.get("step_type", "action")),
                evidence=ev_req,
                verify=ver_req,
                approval=app_gate,
            )
        )
    return ChangeRequest(
        change_id=data["change_id"],
        title=data["title"],
        summary=data.get("summary"),
        steps=steps,
    )


def load_expected_mapping(change_id: str) -> dict:
    """Load netbox expected mapping; supports allowed_endpoints list."""
    base = _repo_root() / "samples" / "scenarios" / change_id
    path = base / "netbox_expected_mapping.json"
    if not path.exists():
        base = _repo_root() / "samples" / "scenarios" / "CHG-001"
        path = base / "netbox_expected_mapping.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_cv_outputs(scenario: str) -> dict:
    """Load cv_outputs.json for scenario (e.g. CHG-001_A)."""
    base = _repo_root() / "samples" / "scenarios" / scenario
    path = base / "cv_outputs.json"
    if not path.exists():
        path = _repo_root() / "samples" / "cv_outputs.json"
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_evidence(evidence_id: str, change_id: str = "") -> Path | None:
    """Resolve evidence_id to local path from evidence_index.json."""
    cid = change_id or "CHG-001"
    for base in [
        _repo_root() / "samples" / "scenarios" / cid,
        _repo_root() / "samples" / "scenarios" / "CHG-001",
        _repo_root() / "samples",
    ]:
        idx_path = base / "evidence_index.json"
        if idx_path.exists():
            data = json.loads(idx_path.read_text(encoding="utf-8"))
            entries = data.get("entries", data) if isinstance(data, dict) else data
            if isinstance(entries, list):
                for e in entries:
                    if e.get("evidence_id") == evidence_id:
                        raw = e.get("path", e.get("uri", ""))
                        p = (base / raw).resolve() if raw else None
                        if p and p.exists():
                            return p
            elif isinstance(entries, dict) and evidence_id in entries:
                raw = entries[evidence_id].get("path", entries[evidence_id].get("uri", ""))
                p = (base / raw).resolve() if raw else None
                if p and p.exists():
                    return p
    img_dir = _repo_root() / "samples" / "images"
    for ext in (".png", ".jpg", ".jpeg"):
        p = img_dir / f"{evidence_id}{ext}"
        if p.exists():
            return p
    return None
