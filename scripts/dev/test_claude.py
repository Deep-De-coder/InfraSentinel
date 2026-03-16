#!/usr/bin/env python3
"""Claude connectivity check: verify ANTHROPIC_API_KEY and Messages API reachability."""
import sys

import httpx

from packages.core.config import get_settings


def main() -> None:
    api_key = get_settings().anthropic_api_key or ""
    if not api_key:
        print("ANTHROPIC_API_KEY is not set. Add it to .env in the project root.", file=sys.stderr)
        sys.exit(1)

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "Reply exactly: OK"}],
            },
            timeout=30,
        )
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 200:
        data = resp.json()
        if data.get("content") and len(data["content"]) > 0:
            print("CLAUDE_OK")
            return
        print("Unexpected response: no content", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)

    err_msg = resp.text
    err_lower = err_msg.lower()
    if "credit" in err_lower or "balance" in err_lower or "insufficient" in err_lower:
        print("CREDITS_REQUIRED: Buy prepaid credits in Anthropic Console -> Billing/Credits", file=sys.stderr)
    print(err_msg, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
