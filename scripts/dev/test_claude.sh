#!/usr/bin/env bash
# Verify Anthropic API connectivity with a minimal Messages call.
# Reads ANTHROPIC_API_KEY and ANTHROPIC_MODEL from infra/env/.env.dev.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

ENV_DEV="infra/env/.env.dev"

if [ ! -f "$ENV_DEV" ]; then
  echo "ERROR: $ENV_DEV not found."
  echo "Run: bash scripts/dev/create_env_dev.sh"
  exit 1
fi

# Load env (without printing values)
set -a
# shellcheck source=/dev/null
. "$ENV_DEV"
set +a

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set in $ENV_DEV"
  exit 1
fi

MODEL="${ANTHROPIC_MODEL:-claude-sonnet-4-6}"
echo "=== Claude connectivity test (model: $MODEL) ==="

# Try anthropic SDK first; fall back to stdlib urllib (no pip needed).
SCRIPT_DIR_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if python3 -c "import anthropic" 2>/dev/null; then
  USE_SDK=1
else
  echo "anthropic SDK not found — trying to install..."
  if python3 -m pip install --quiet anthropic 2>/dev/null; then
    echo "anthropic SDK installed."
    USE_SDK=1
  else
    echo "pip unavailable — falling back to stdlib urllib (no extra deps)."
    USE_SDK=0
  fi
fi

if [ "${USE_SDK}" -eq 1 ]; then
  python3 - <<'PYEOF'
import os, sys
import anthropic

model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

client = anthropic.Anthropic(api_key=api_key)

try:
    msg = client.messages.create(
        model=model,
        max_tokens=16,
        messages=[{"role": "user", "content": "Reply with exactly: InfraSentinel Claude OK"}],
    )
    text = msg.content[0].text.strip() if msg.content else ""
    print(f"Response: {text}")
    print("CLAUDE_OK")
except anthropic.APIStatusError as e:
    err_lower = str(e).lower()
    if "credit" in err_lower or "balance" in err_lower or "insufficient" in err_lower:
        print(
            "CREDITS_REQUIRED: Buy prepaid credits in Anthropic Console -> Billing/Credits",
            file=sys.stderr,
        )
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
else
  python3 "${SCRIPT_DIR_PY}/_test_claude_urllib.py"
fi
