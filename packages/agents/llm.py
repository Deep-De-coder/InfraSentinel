"""LLM client for text generation (Claude/LiteLLM). Mock mode = deterministic."""

from __future__ import annotations

from packages.core.models.steps import StepDefinition


def get_llm_provider() -> str:
    """Read LLM_PROVIDER from env: anthropic|litellm|mock."""
    import os
    return os.environ.get("LLM_PROVIDER", "mock").lower()


def generate_tech_prompt(step_def: StepDefinition) -> str:
    """Generate technician-facing prompt. Mock: deterministic. Prod: Claude."""
    provider = get_llm_provider()
    if provider == "mock":
        from packages.agents.mop import mop_advice
        out = mop_advice(step_def)
        return out.get("tech_prompt", step_def.description)
    if provider in ("anthropic", "litellm"):
        return _llm_tech_prompt(step_def)
    return step_def.description


def generate_escalation_text(step_def: StepDefinition, cmdb_reason: str) -> str:
    """Generate escalation text for ticketing. Mock: deterministic. Prod: Claude."""
    provider = get_llm_provider()
    if provider == "mock":
        from packages.agents.cmdb import cmdb_advice
        out = cmdb_advice(step_def, {"match": False, "reason": cmdb_reason})
        return out.get("escalation_text", f"CMDB mismatch: {cmdb_reason}") or ""
    if provider in ("anthropic", "litellm"):
        return _llm_escalation(step_def, cmdb_reason)
    return f"CMDB mismatch for step {step_def.step_id}: {cmdb_reason}. Approval required."


def _llm_tech_prompt(step_def: StepDefinition) -> str:
    """Call Claude/LiteLLM for tech prompt. Fallback to deterministic if no key."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LITELLM_API_KEY")
    if not api_key:
        from packages.agents.mop import mop_advice
        return mop_advice(step_def).get("tech_prompt", step_def.description)
    try:
        return _call_llm(
            f"Write a short technician instruction for this MOP step. One sentence only. Step: {step_def.description}",
            max_tokens=80,
        )
    except Exception:
        from packages.agents.mop import mop_advice
        return mop_advice(step_def).get("tech_prompt", step_def.description)


def _llm_escalation(step_def: StepDefinition, cmdb_reason: str) -> str:
    """Call Claude/LiteLLM for escalation text. Fallback to deterministic if no key."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LITELLM_API_KEY")
    if not api_key:
        from packages.agents.cmdb import cmdb_advice
        out = cmdb_advice(step_def, {"match": False, "reason": cmdb_reason})
        return out.get("escalation_text", f"CMDB mismatch: {cmdb_reason}") or ""
    try:
        return _call_llm(
            f"Write a brief escalation note for ticketing. Step {step_def.step_id}, reason: {cmdb_reason}. One sentence.",
            max_tokens=100,
        )
    except Exception:
        from packages.agents.cmdb import cmdb_advice
        out = cmdb_advice(step_def, {"match": False, "reason": cmdb_reason})
        return out.get("escalation_text", f"CMDB mismatch: {cmdb_reason}") or ""


def _call_llm(prompt: str, max_tokens: int = 80) -> str:
    """Call Anthropic or LiteLLM. Cloud-agnostic."""
    import os
    provider = get_llm_provider()
    base_url = os.environ.get("LITELLM_BASE_URL", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LITELLM_API_KEY", "")

    if provider == "anthropic" and api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            if msg.content and len(msg.content) > 0:
                return msg.content[0].text.strip()
        except ImportError:
            pass

    if provider == "litellm" and base_url and api_key:
        try:
            import httpx
            resp = httpx.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                return content.strip()
        except Exception:
            pass

    return prompt[:max_tokens]
