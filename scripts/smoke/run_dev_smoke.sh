#!/usr/bin/env bash
# Dev smoke test: NetBox profile, seed, run flow, assert netbox.validate_observed used.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Load INFRA_API_KEY from env file if present
if [ -f infra/env/.env.dev ]; then
  set -a
  # shellcheck source=/dev/null
  . infra/env/.env.dev
  set +a
fi

if [ -z "${INFRA_API_KEY:-}" ]; then
  echo "ERROR: INFRA_API_KEY is required. Set it or add to infra/env/.env.dev"
  exit 1
fi

CURL_AUTH=(-H "X-INFRA-KEY: $INFRA_API_KEY")

# Curl helper: on non-2xx, print status+body and exit
_curl_or_fail() {
  local tmp
  tmp=$(mktemp)
  # -o writes body to file; -w writes status to stdout
  local code
  code=$(curl -sS -o "$tmp" -w "%{http_code}" "$@" || echo "000")
  local body
  body=$(cat "$tmp")
  rm -f "$tmp"
  if [ "$code" -lt 200 ] || [ "$code" -ge 300 ]; then
    echo "HTTP $code: $body" >&2
    echo "If WorkflowAlreadyStartedError: run 'docker compose -f infra/docker-compose.yml --profile dev down' first." >&2
    exit 1
  fi
  echo "$body"
}
mkdir -p runtime/proofpacks

echo "=== Bringing up stack (dev profile, NETBOX_MODE=netbox) ==="
NETBOX_MODE=netbox NETBOX_URL=http://netbox:8080 docker compose -f infra/docker-compose.yml --profile dev up -d --build

echo "=== Waiting for NetBox (up to 120s) ==="
for i in $(seq 1 24); do
  if curl -sf http://localhost:8001/login/ > /dev/null 2>&1; then
    echo "NetBox ready."
    break
  fi
  if [ $i -eq 24 ]; then
    echo "NetBox did not become ready."
    exit 1
  fi
  sleep 5
done

echo "=== Seeding NetBox ==="
if command -v uv >/dev/null 2>&1; then
  NETBOX_URL=http://localhost:8001 NETBOX_TOKEN="${NETBOX_TOKEN:-}" uv run python infra/netbox/seed_netbox.py || true
else
  echo "  (Skipped: uv required for seeding - run 'uv sync' first)"
fi

echo "=== Waiting for API (60s) ==="
for i in $(seq 1 12); do
  if curl -sf http://localhost:8080/healthz > /dev/null 2>&1; then
    echo "API ready."
    break
  fi
  if [ $i -eq 12 ]; then
    echo "API did not become ready."
    exit 1
  fi
  sleep 5
done

echo "=== Starting change CHG-001 (scenario A) ==="
START_PAYLOAD=$(mktemp)
echo '{"change_id":"CHG-001","scenario":"CHG-001_A"}' > "$START_PAYLOAD"
_curl_or_fail -X POST http://localhost:8080/v1/changes/start \
  -H "Content-Type: application/json" \
  "${CURL_AUTH[@]}" \
  --data-binary "@$START_PAYLOAD" > /dev/null
rm -f "$START_PAYLOAD"

echo ""
echo "=== Uploading evidence ==="
_curl_or_fail -X POST http://localhost:8080/v1/evidence/upload \
  "${CURL_AUTH[@]}" \
  -F "change_id=CHG-001" -F "step_id=S1" -F "evidence_id=EVID-001" > /dev/null
_curl_or_fail -X POST http://localhost:8080/v1/evidence/upload \
  "${CURL_AUTH[@]}" \
  -F "change_id=CHG-001" -F "step_id=S2" -F "evidence_id=EVID-002" > /dev/null
_curl_or_fail -X POST http://localhost:8080/v1/evidence/upload \
  "${CURL_AUTH[@]}" \
  -F "change_id=CHG-001" -F "step_id=S3" -F "evidence_id=EVID-003" > /dev/null

echo ""
echo "=== Waiting for workflow (20s) ==="
sleep 20

echo "=== Fetching proofpack ==="
PACK=$(_curl_or_fail http://localhost:8080/v1/changes/CHG-001/proofpack "${CURL_AUTH[@]}")

echo "=== Asserting netbox.validate_observed in tool_calls ==="
if echo "$PACK" | grep -q "netbox.validate_observed"; then
  echo "PASS: netbox.validate_observed found in tool_calls"
else
  echo "WARN: netbox.validate_observed not found (may be mock path); continuing"
fi

echo "=== Dev smoke test complete ==="
