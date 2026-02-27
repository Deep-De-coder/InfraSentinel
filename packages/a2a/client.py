"""A2A HTTP client with retries and timeouts."""

from __future__ import annotations

import uuid

import httpx

from packages.a2a.schema import AgentCard, A2AResponse


class A2AClient:
    """HTTP client for A2A agent services."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries

    def get_agent_card(self) -> AgentCard:
        """Fetch agent card from GET /a2a/agent-card."""
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self._base_url}/a2a/agent-card")
            resp.raise_for_status()
            data = resp.json()
            return AgentCard.model_validate(data)

    async def send_async(
        self,
        agent: str,
        input_data: dict,
        context: dict | None = None,
    ) -> A2AResponse:
        """Send message to POST /a2a/message/send (async)."""
        payload = {
            "message_id": str(uuid.uuid4()),
            "agent": agent,
            "input": input_data,
            "context": context or {},
        }
        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    resp = await client.post(
                        f"{self._base_url}/a2a/message/send",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return A2AResponse.model_validate(data)
                except (httpx.HTTPError, httpx.RequestError) as e:
                    last_err = e
                    if attempt < self._max_retries:
                        continue
        raise last_err or RuntimeError("A2A send failed")

    def send(
        self,
        agent: str,
        input_data: dict,
        context: dict | None = None,
    ) -> A2AResponse:
        """Send message to POST /a2a/message/send (sync)."""
        payload = {
            "message_id": str(uuid.uuid4()),
            "agent": agent,
            "input": input_data,
            "context": context or {},
        }
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.post(
                        f"{self._base_url}/a2a/message/send",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return A2AResponse.model_validate(data)
            except (httpx.HTTPError, httpx.RequestError) as e:
                last_err = e
                if attempt < self._max_retries:
                    continue
        raise last_err or RuntimeError("A2A send failed")
