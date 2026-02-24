"""Workflow scenario tests (lightweight, mock workflow driver)."""

import os

import pytest

from packages.core.fixtures.loaders import load_change, load_cv_outputs, load_expected_mapping
from packages.core.logic.proofpack import update_proofpack
from packages.core.logic.state_machine import (
    apply_cmdb_validation,
    apply_cv_result,
    on_evidence_uploaded,
    start_step,
)
from packages.core.models.proofpack import EvidenceRef, ProofPack
from packages.core.models.steps import StepDefinition, StepResult, StepStatus


@pytest.fixture(autouse=True)
def set_scenario_a():
    os.environ["SCENARIO"] = "CHG-001_A"
    yield
    os.environ.pop("SCENARIO", None)


def test_load_change_chg001() -> None:
    change = load_change("CHG-001")
    assert change.change_id == "CHG-001"
    assert len(change.steps) == 3
    assert change.steps[0].step_id == "S1"
    assert change.steps[0].evidence is not None
    assert change.steps[0].verify is not None


def test_load_cv_outputs_scenario_a() -> None:
    data = load_cv_outputs("CHG-001_A")
    assert "EVID-001" in data
    assert data["EVID-001"]["port_label"] == "24"
    assert data["EVID-001"]["port_confidence"] >= 0.9


def test_load_expected_mapping_allowed_endpoints() -> None:
    data = load_expected_mapping("CHG-001")
    assert "allowed_endpoints" in data
    assert len(data["allowed_endpoints"]) >= 1


def test_happy_path_s2_verified() -> None:
    """Scenario A: S1 EVID-001, S2 EVID-002, S3 EVID-003 => S2 VERIFIED."""
    change = load_change("CHG-001")
    cv_data = load_cv_outputs("CHG-001_A")
    step_def = change.steps[1]
    result = StepResult(
        change_id="CHG-001",
        step_id="S2",
        status=start_step(step_def),
        evidence_ids=[],
    )
    result = on_evidence_uploaded(result, "EVID-002")

    class PortOut:
        pass

    po = PortOut()
    po.panel_id = cv_data["EVID-002"]["panel_id"]
    po.port_label = cv_data["EVID-002"]["port_label"]
    po.confidence = cv_data["EVID-002"]["port_confidence"]

    class TagOut:
        pass

    to = TagOut()
    to.cable_tag = cv_data["EVID-002"]["cable_tag"]
    to.confidence = cv_data["EVID-002"]["cable_confidence"]

    result = apply_cv_result(step_def, result, po, to)
    assert result.status == StepStatus.VERIFYING
    assert result.observed_port_label == "24"

    class CmdbOut:
        match = True
        reason = "OK"

    result = apply_cmdb_validation(step_def, result, CmdbOut())
    assert result.status == StepStatus.VERIFIED


def test_retake_path_s2_needs_retake_then_verified() -> None:
    """Scenario C: EVID-002 low conf => NEEDS_RETAKE, EVID-002-RETAKE => VERIFIED."""
    change = load_change("CHG-001")
    cv_data = load_cv_outputs("CHG-001_C")
    step_def = change.steps[1]
    result = StepResult(
        change_id="CHG-001",
        step_id="S2",
        status=start_step(step_def),
        evidence_ids=[],
    )
    result = on_evidence_uploaded(result, "EVID-002")

    class PortOut:
        pass

    po = PortOut()
    po.panel_id = cv_data["EVID-002"].get("panel_id")
    po.port_label = cv_data["EVID-002"].get("port_label")
    po.confidence = cv_data["EVID-002"].get("port_confidence", 0)

    class TagOut:
        pass

    to = TagOut()
    to.cable_tag = cv_data["EVID-002"].get("cable_tag")
    to.confidence = cv_data["EVID-002"].get("cable_confidence", 0)

    result = apply_cv_result(step_def, result, po, to)
    assert result.status == StepStatus.NEEDS_RETAKE

    result = on_evidence_uploaded(result, "EVID-002-RETAKE")
    po.port_label = cv_data["EVID-002-RETAKE"]["port_label"]
    po.confidence = cv_data["EVID-002-RETAKE"]["port_confidence"]
    to.cable_tag = cv_data["EVID-002-RETAKE"]["cable_tag"]
    to.confidence = cv_data["EVID-002-RETAKE"]["cable_confidence"]
    result = apply_cv_result(step_def, result, po, to)
    assert result.status == StepStatus.VERIFYING


def test_proofpack_update() -> None:
    proofpack = ProofPack(change_id="CHG-001")
    result = StepResult(
        change_id="CHG-001",
        step_id="S1",
        status=StepStatus.VERIFIED,
        evidence_ids=["EVID-001"],
    )
    ev_ref = EvidenceRef(evidence_id="EVID-001", path="evidence/EVID-001")
    updated = update_proofpack(proofpack, "CHG-001", result, ev_ref)
    assert len(updated.steps) == 1
    assert updated.summary["verified_steps"] == 1
    assert len(updated.evidence_index) == 1
