"""Stdlib-only Claude connectivity check (used by test_claude.sh when anthropic SDK unavailable)."""
import json
import os
import sys
import urllib.error
import urllib.request

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

if not api_key:
    print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
    sys.exit(1)

payload = json.dumps({
    "model": model,
    "max_tokens": 16,
    "messages": [{"role": "user", "content": "Reply with exactly: InfraSentinel Claude OK"}],
}).encode()

req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=payload,
    headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        d = json.load(resp)
        text = d["content"][0]["text"].strip()
        print(f"Response: {text}")
        print("CLAUDE_OK")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    lower = body.lower()
    if "credit" in lower or "balance" in lower or "insufficient" in lower:
        print(
            "CREDITS_REQUIRED: Buy prepaid credits in Anthropic Console -> Billing/Credits",
            file=sys.stderr,
        )
    print(f"HTTP {e.code}: {body}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
