#!/usr/bin/env bash
# Start InfraSentinel stack using the dev env file (Claude-enabled, mock CV).
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

echo "=== Starting InfraSentinel (dev / Claude mode) ==="
docker compose -f infra/docker-compose.yml --env-file "$ENV_DEV" up -d --build

echo ""
echo "=== Key service URLs ==="
echo "  API:           http://localhost:8080"
echo "  Temporal UI:   http://localhost:8088"
echo "  MinIO console: http://localhost:9001"
echo ""
echo "Logs: docker compose -f infra/docker-compose.yml logs -f"
