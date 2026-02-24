"""Runtime persistence for proofpacks and step results (mock mode)."""

from __future__ import annotations

import json
from pathlib import Path

from packages.core.models.proofpack import ProofPack, render_proofpack_json
from packages.core.models.steps import StepResult


def _runtime_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "runtime"


def _proofpack_path(change_id: str) -> Path:
    d = _runtime_dir() / "proofpacks"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{change_id}.json"


def save_proofpack(proofpack: ProofPack) -> None:
    path = _proofpack_path(proofpack.change_id)
    path.write_text(json.dumps(render_proofpack_json(proofpack), indent=2), encoding="utf-8")


def load_proofpack(change_id: str) -> ProofPack | None:
    path = _proofpack_path(change_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProofPack.model_validate(data)


def append_step_result_log(step_result: StepResult) -> None:
    path = _runtime_dir() / "step_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if path.exists():
        entries = json.loads(path.read_text(encoding="utf-8"))
    entries.append(step_result.model_dump(mode="json"))
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def get_scenario_config() -> dict:
    path = _runtime_dir() / "config.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def set_scenario_config(change_id: str, scenario: str | None) -> None:
    path = _runtime_dir() / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = get_scenario_config()
    data[change_id] = {"scenario": scenario or "CHG-001_A"}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
