#!/usr/bin/env bash
# One-command Claude quickstart:
#   1) create/update infra/env/.env.dev
#   2) verify Anthropic API connectivity
#   3) start the stack (dev env, Claude-enabled)
#   4) run smoke test (CHG-001_A)
#   5) verify Claude was used in logs
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "========================================"
echo " InfraSentinel — Claude dev quickstart"
echo "========================================"
echo ""

echo "--- Step 1/5: Env setup ---"
bash scripts/dev/create_env_dev.sh
echo ""

echo "--- Step 2/5: Claude connectivity test ---"
bash scripts/dev/test_claude.sh
echo ""

echo "--- Step 3/5: Start stack ---"
bash scripts/dev/up_dev.sh
echo ""

echo "--- Step 4/5: Smoke test (CHG-001_A) ---"
bash scripts/smoke/run_smoke.sh
echo ""

echo "--- Step 5/5: Verify Claude usage ---"
bash scripts/dev/verify_claude_used.sh
echo ""

echo "========================================"
echo " SUCCESS: InfraSentinel running with Claude."
echo "  API:      http://localhost:8080"
echo "  Temporal: http://localhost:8088"
echo "  MinIO:    http://localhost:9001"
echo "========================================"
