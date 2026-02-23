from __future__ import annotations

from dataclasses import dataclass

from packages.core.config import Settings


@dataclass
class AgentRuntime:
    provider: str
    model_name: str


def build_agent_runtime(settings: Settings) -> AgentRuntime:
    if settings.anthropic_api_key:
        return AgentRuntime(provider="anthropic", model_name="claude-3-5-sonnet-latest")
    return AgentRuntime(provider="mock", model_name="deterministic-mock")
