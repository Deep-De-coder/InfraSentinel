"""A2A-style agent message schema and client."""

__version__ = "0.1.0"

from packages.a2a.schema import AgentCard, A2AMessage, A2AResponse
from packages.a2a.client import A2AClient

__all__ = ["AgentCard", "A2AMessage", "A2AResponse", "A2AClient"]
