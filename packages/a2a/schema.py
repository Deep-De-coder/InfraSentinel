"""Minimal A2A message schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    """Agent capability card exposed at GET /a2a/agent-card."""

    name: str
    version: str
    capabilities: list[str] = Field(default_factory=list)
    endpoints: dict[str, str] = Field(default_factory=dict)


class A2AMessage(BaseModel):
    """Incoming message to an agent."""

    message_id: str | None = None
    conversation_id: str | None = None
    agent: str
    input: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)


class A2AResponse(BaseModel):
    """Agent response."""

    message_id: str | None = None
    status: str = "ok"
    output: dict = Field(default_factory=dict)
    notes: str | None = None
