"""Integration tests for A2A agent services (in-process, no docker)."""

import pytest
from fastapi.testclient import TestClient

from packages.a2a.schema import A2AMessage
from services.a2a_mop_agent.server import app as mop_app
from services.a2a_vision_agent.server import app as vision_app
from services.a2a_cmdb_agent.server import app as cmdb_app


def test_mop_agent_card() -> None:
    client = TestClient(mop_app)
    resp = client.get("/a2a/agent-card")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "MOPComplianceAgent"
    assert "capabilities" in data


def test_mop_agent_send() -> None:
    client = TestClient(mop_app)
    msg = A2AMessage(
        agent="mop",
        input={
            "step_def": {
                "step_id": "S1",
                "description": "Verify panel port",
                "step_type": "port_verify",
                "evidence": {"kind": "photo", "count": 1},
                "verify": {"requires_port_label": True, "requires_cable_tag": True, "min_confidence": 0.75},
                "approval": {"required": True, "on_blocked": True},
            },
        },
        context={},
    )
    resp = client.post("/a2a/message/send", json=msg.model_dump(mode="json"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "tech_prompt" in data["output"]
    assert "required_evidence_summary" in data["output"]


def test_vision_agent_card() -> None:
    client = TestClient(vision_app)
    resp = client.get("/a2a/agent-card")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "VisionVerifierAgent"


def test_vision_agent_send() -> None:
    client = TestClient(vision_app)
    msg = A2AMessage(
        agent="vision",
        input={
            "step_def": {
                "step_id": "S1",
                "description": "Verify",
                "step_type": "port_verify",
                "evidence": {"kind": "photo", "count": 1},
                "verify": {"requires_port_label": True, "requires_cable_tag": True, "min_confidence": 0.75},
                "approval": None,
            },
            "quality_metrics": None,
            "cv_port_out": {"panel_id": "P1", "port_label": "24", "confidence": 0.9},
            "cv_tag_out": {"cable_tag": "T1", "confidence": 0.9},
        },
        context={},
    )
    resp = client.post("/a2a/message/send", json=msg.model_dump(mode="json"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["output"]["decision"] == "accept"


def test_cmdb_agent_card() -> None:
    client = TestClient(cmdb_app)
    resp = client.get("/a2a/agent-card")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "CMDBValidatorAgent"


def test_cmdb_agent_send_proceed() -> None:
    client = TestClient(cmdb_app)
    msg = A2AMessage(
        agent="cmdb",
        input={
            "step_def": {
                "step_id": "S1",
                "description": "Verify",
                "step_type": "port_verify",
                "evidence": None,
                "verify": None,
                "approval": None,
            },
            "cmdb_out": {"match": True, "reason": "OK"},
        },
        context={},
    )
    resp = client.post("/a2a/message/send", json=msg.model_dump(mode="json"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["output"]["decision"] == "proceed"


def test_cmdb_agent_send_block() -> None:
    client = TestClient(cmdb_app)
    msg = A2AMessage(
        agent="cmdb",
        input={
            "step_def": {
                "step_id": "S1",
                "description": "Verify",
                "step_type": "port_verify",
                "evidence": None,
                "verify": None,
                "approval": {"required": True, "on_blocked": True},
            },
            "cmdb_out": {"match": False, "reason": "Port 99 not in mapping"},
        },
        context={},
    )
    resp = client.post("/a2a/message/send", json=msg.model_dump(mode="json"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["output"]["decision"] == "block"
    assert "escalation_text" in data["output"]
