#!/usr/bin/env bash
# One-shot smoke test: mock mode end-to-end.
# Starts stack if needed, runs scenario A, asserts S2 verified.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Require jq
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required but not installed."
  echo "Install jq: https://stedolan.github.io/jq/download/"
  echo "  - macOS: brew install jq"
  echo "  - Ubuntu/Debian: sudo apt-get install jq"
  echo "  - Windows: choco install jq, or use Git Bash with jq"
  exit 1
fi

# Load env for API key (used in curl headers)
if [ -f infra/env/.env.mock ]; then
  set -a
  # shellcheck source=/dev/null
  . infra/env/.env.mock
  set +a
fi

CURL_AUTH=()
[ -n "${INFRA_API_KEY:-}" ] && CURL_AUTH=(-H "X-INFRA-KEY: $INFRA_API_KEY")

mkdir -p runtime/proofpacks

# Start stack if API is not running
if ! curl -sf http://localhost:8080/healthz >/dev/null 2>&1; then
  echo "=== Stack not running, bringing up (mock) ==="
  if [ -f infra/env/.env.mock ]; then
    docker compose -f infra/docker-compose.yml --env-file infra/env/.env.mock up -d --build
  else
    docker compose -f infra/docker-compose.yml up -d --build
  fi
else
  echo "=== Stack already running ==="
fi

echo "=== Waiting for API (up to 60s) ==="
for i in $(seq 1 12); do
  if curl -sf http://localhost:8080/healthz >/dev/null 2>&1; then
    echo "API ready."
    break
  fi
  if [ $i -eq 12 ]; then
    echo "API did not become ready."
    exit 1
  fi
  sleep 5
done

echo "=== Starting change CHG-001 ==="
curl -sf -X POST http://localhost:8080/v1/changes/start \
  "${CURL_AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d '{"change_id":"CHG-001","scenario":"CHG-001_A"}'

echo ""
echo "=== Uploading evidence S1 (EVID-001) ==="
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  "${CURL_AUTH[@]}" \
  -F "change_id=CHG-001" -F "step_id=S1" -F "evidence_id=EVID-001"

echo ""
echo "=== Uploading evidence S2 (EVID-002) ==="
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  "${CURL_AUTH[@]}" \
  -F "change_id=CHG-001" -F "step_id=S2" -F "evidence_id=EVID-002"

echo ""
echo "=== Uploading evidence S3 (EVID-003) ==="
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  "${CURL_AUTH[@]}" \
  -F "change_id=CHG-001" -F "step_id=S3" -F "evidence_id=EVID-003"

echo ""
echo "=== Waiting for workflow (15s) ==="
sleep 15

echo "=== Fetching proofpack ==="
PACK=$(curl -sf http://localhost:8080/v1/changes/CHG-001/proofpack "${CURL_AUTH[@]}")

echo "=== Asserting S2 status == verified ==="
S2_STATUS=$(echo "$PACK" | jq -r '.steps[] | select(.step_id=="S2") | .status // empty')
if [ "$S2_STATUS" != "verified" ]; then
  echo "FAIL: S2 status is '$S2_STATUS', expected verified"
  exit 1
fi
echo "PASS: S2 is verified"

echo "=== Asserting false-green guard (S1/S3 confidence if present) ==="
# S1 and S3 are port_verify steps; ensure confidence meets threshold (0.75) when present
for step in S1 S3; do
  conf=$(echo "$PACK" | jq -r ".steps[] | select(.step_id==\"$step\") | .confidence // empty")
  if [ -n "$conf" ] && [ "$conf" != "null" ]; then
    if ! python3 -c "exit(0 if float('$conf') >= 0.75 else 1)" 2>/dev/null; then
      echo "FAIL: $step confidence $conf < 0.75 (false-green guard)"
      exit 1
    fi
    echo "PASS: $step confidence $conf >= 0.75"
  fi
done

echo "=== Smoke test PASSED ==="
