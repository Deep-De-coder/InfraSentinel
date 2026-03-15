#!/usr/bin/env bash
# One-command mock mode: create env, bring up stack, run smoke test.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Create .env.mock from example if missing (with generated keys)
echo "=== Ensuring infra/env/.env.mock exists ==="
python3 scripts/dev/ensure_env_mock.py || true

echo "=== Bringing up stack ==="
docker compose -f infra/docker-compose.yml --env-file infra/env/.env.mock up -d --build
echo ""
echo "=== Key service URLs ==="
echo "  API:           http://localhost:8080"
echo "  Temporal UI:   http://localhost:8088"
echo "  MinIO console: http://localhost:9001"
echo ""

echo "=== Running smoke test ==="
bash scripts/smoke/run_smoke.sh

echo ""
echo "SUCCESS: InfraSentinel mock mode is running."
echo "  Proofpack: http://localhost:8080/v1/changes/CHG-001/proofpack"
echo "  API:       http://localhost:8080"
echo "  Temporal:  http://localhost:8088"
echo "  MinIO:     http://localhost:9001"
