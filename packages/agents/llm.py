"""LLM client for text generation (Claude/LiteLLM). Mock mode = deterministic.

Error classification:
  - AuthenticationError  → fail immediately (bad API key, no retry)
  - RateLimitError       → retry up to 3x with exponential backoff (1s, 2s, 4s)
  - APIConnectionError   → retry up to 2x then fall back to mock
  - Other exceptions     → fall back to mock + log warning
"""

from __future__ import annotations

import logging
import os
import time

from opentelemetry import trace

from packages.core.models.steps import StepDefinition

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


def get_llm_provider() -> str:
    """Read LLM_PROVIDER from env: anthropic|litellm|mock."""
    return os.environ.get("LLM_PROVIDER", "mock").lower()


def _get_settings():  # type: ignore[return]
    try:
        from packages.core.config import get_settings

        return get_settings()
    except Exception:
        return None


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
    """Call Claude/LiteLLM for tech prompt. Falls back to deterministic on failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LITELLM_API_KEY")
    if not api_key:
        from packages.agents.mop import mop_advice

        return mop_advice(step_def).get("tech_prompt", step_def.description)
    prompt = (
        f"Write a short technician instruction for this MOP step. "
        f"One sentence only. Step: {step_def.description}"
    )
    result, fallback_used = _call_llm(prompt, max_tokens=80)
    if fallback_used:
        from packages.agents.mop import mop_advice

        return mop_advice(step_def).get("tech_prompt", step_def.description)
    return result


def _llm_escalation(step_def: StepDefinition, cmdb_reason: str) -> str:
    """Call Claude/LiteLLM for escalation text. Falls back to deterministic on failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LITELLM_API_KEY")
    if not api_key:
        from packages.agents.cmdb import cmdb_advice

        out = cmdb_advice(step_def, {"match": False, "reason": cmdb_reason})
        return out.get("escalation_text", f"CMDB mismatch: {cmdb_reason}") or ""
    prompt = (
        f"Write a brief escalation note for ticketing. "
        f"Step {step_def.step_id}, reason: {cmdb_reason}. One sentence."
    )
    result, fallback_used = _call_llm(prompt, max_tokens=100)
    if fallback_used:
        from packages.agents.cmdb import cmdb_advice

        out = cmdb_advice(step_def, {"match": False, "reason": cmdb_reason})
        return out.get("escalation_text", f"CMDB mismatch: {cmdb_reason}") or ""
    return result


def _call_llm(prompt: str, max_tokens: int = 80) -> tuple[str, bool]:
    """Call Anthropic or LiteLLM.  Returns (text, fallback_used).

    Never raises unless LLM_HARD_FAIL=true (in which case AuthenticationError
    and exhausted-retry errors propagate immediately).
    """
    provider = get_llm_provider()
    base_url = os.environ.get("LITELLM_BASE_URL", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LITELLM_API_KEY", "")
    settings = _get_settings()
    hard_fail: bool = getattr(settings, "llm_hard_fail", False) if settings else False
    model = (
        getattr(settings, "anthropic_model", None) or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    )

    with _tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.prompt_length", len(prompt))

        t0 = time.monotonic()
        result, fallback_used = _dispatch_llm(
            provider, api_key, base_url, model, prompt, max_tokens, hard_fail
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        span.set_attribute("llm.latency_ms", latency_ms)
        span.set_attribute("llm.fallback_used", fallback_used)
        span.set_attribute("llm.success", not fallback_used)

        logger.info(
            "LLM call: provider=%s model=%s prompt_len=%d latency_ms=%d "
            "success=%s fallback_used=%s",
            provider,
            model,
            len(prompt),
            latency_ms,
            not fallback_used,
            fallback_used,
        )

    return result, fallback_used


def _dispatch_llm(
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    hard_fail: bool,
) -> tuple[str, bool]:
    if provider == "anthropic" and api_key:
        return _call_anthropic(api_key, model, prompt, max_tokens, hard_fail)

    if provider == "litellm" and base_url and api_key:
        return _call_litellm(base_url, api_key, model, prompt, max_tokens, hard_fail)

    return prompt[:max_tokens], True


def _call_anthropic(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    hard_fail: bool,
) -> tuple[str, bool]:
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed")
        return "", True

    backoff_schedule = [1, 2, 4]
    client = anthropic.Anthropic(api_key=api_key)

    attempt = 0
    while True:
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip() if msg.content else ""
            return text, False

        except anthropic.AuthenticationError as exc:
            logger.error("Anthropic authentication failed — check ANTHROPIC_API_KEY")
            if hard_fail:
                raise
            return "", True

        except anthropic.RateLimitError as exc:
            if attempt < len(backoff_schedule):
                wait = backoff_schedule[attempt]
                logger.warning("Anthropic rate limit; retrying in %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                attempt += 1
                continue
            logger.warning("Anthropic rate limit exhausted after retries")
            if hard_fail:
                raise
            return "", True

        except anthropic.APIConnectionError as exc:
            if attempt < 2:
                wait = backoff_schedule[attempt]
                logger.warning("Anthropic connection error; retrying in %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                attempt += 1
                continue
            logger.warning("Anthropic connection failed after retries: %s", exc)
            if hard_fail:
                raise
            return "", True

        except Exception as exc:
            logger.warning("Anthropic call failed: %s", exc)
            if hard_fail:
                raise
            return "", True


def _call_litellm(
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    hard_fail: bool,
) -> tuple[str, bool]:
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed")
        return "", True

    try:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip(), False
        return "", True
    except Exception as exc:
        logger.warning("LiteLLM call failed: %s", exc)
        if hard_fail:
            raise
        return "", True
