#!/usr/bin/env bash
# Check worker logs for evidence that Claude / Anthropic was invoked.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="infra/docker-compose.yml"
ENV_DEV="infra/env/.env.dev"

ENV_FLAG=()
if [ -f "$ENV_DEV" ]; then
  ENV_FLAG=(--env-file "$ENV_DEV")
fi

# Determine the worker container name from compose
WORKER_CONTAINER="$(docker compose -f "$COMPOSE_FILE" "${ENV_FLAG[@]}" ps --format json 2>/dev/null \
  | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    name = obj.get('Name', '') or obj.get('name', '')
    if 'worker' in name.lower():
        print(name)
        break
" 2>/dev/null || true)"

if [ -z "$WORKER_CONTAINER" ]; then
  # Fall back to well-known container name used in docker-compose.yml
  WORKER_CONTAINER="infrasentinel-worker"
fi

echo "=== Checking Claude usage in container: $WORKER_CONTAINER ==="

LOG_OUTPUT="$(docker logs "$WORKER_CONTAINER" 2>&1 | tail -n 200 || true)"

if echo "$LOG_OUTPUT" | grep -qiE "anthropic|claude|LLM_PROVIDER=anthropic"; then
  echo "CLAUDE_CONFIRMED: Anthropic/Claude usage detected in worker logs."
  echo "$LOG_OUTPUT" | grep -iE "anthropic|claude|LLM_PROVIDER=anthropic" | head -n 10
else
  echo ""
  echo "WARNING: Could not confirm Claude usage from logs."
  echo "  Ensure infra/env/.env.dev contains:"
  echo "    LLM_PROVIDER=anthropic"
  echo "    ANTHROPIC_API_KEY=<your-key>"
  echo "  Then restart the stack: bash scripts/dev/up_dev.sh"
  echo ""
  echo "  Tail worker logs:"
  echo "    docker compose -f infra/docker-compose.yml logs -f worker"
fi
