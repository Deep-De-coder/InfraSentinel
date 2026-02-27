"""Unit tests for A2A schema serialization."""

import pytest

from packages.a2a.schema import AgentCard, A2AMessage, A2AResponse


def test_agent_card_serialization() -> None:
    card = AgentCard(
        name="TestAgent",
        version="0.1.0",
        capabilities=["cap1", "cap2"],
        endpoints={"send": "/a2a/message/send"},
    )
    data = card.model_dump(mode="json")
    assert data["name"] == "TestAgent"
    assert data["version"] == "0.1.0"
    assert "cap1" in data["capabilities"]
    loaded = AgentCard.model_validate(data)
    assert loaded.name == card.name


def test_a2a_message_serialization() -> None:
    msg = A2AMessage(
        message_id="mid-1",
        agent="mop",
        input={"step_def": {"step_id": "S1", "description": "Test"}},
        context={},
    )
    data = msg.model_dump(mode="json")
    assert data["agent"] == "mop"
    assert data["input"]["step_def"]["step_id"] == "S1"
    loaded = A2AMessage.model_validate(data)
    assert loaded.agent == msg.agent


def test_a2a_response_serialization() -> None:
    resp = A2AResponse(
        message_id="mid-1",
        status="ok",
        output={"tech_prompt": "Do X", "required_evidence_summary": "Photo"},
        notes=None,
    )
    data = resp.model_dump(mode="json")
    assert data["status"] == "ok"
    assert data["output"]["tech_prompt"] == "Do X"
    loaded = A2AResponse.model_validate(data)
    assert loaded.status == resp.status
