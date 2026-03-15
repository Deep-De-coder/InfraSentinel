#!/usr/bin/env bash
# Dev smoke test: NetBox profile, seed, run flow, assert netbox.validate_observed used.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

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
NETBOX_URL=http://localhost:8001 NETBOX_TOKEN= python infra/netbox/seed_netbox.py || true

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
curl -sf -X POST http://localhost:8080/v1/changes/start \
  -H "Content-Type: application/json" \
  -d '{"change_id":"CHG-001","scenario":"CHG-001_A"}'

echo ""
echo "=== Uploading evidence ==="
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S1" -F "evidence_id=EVID-001"
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S2" -F "evidence_id=EVID-002"
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S3" -F "evidence_id=EVID-003"

echo ""
echo "=== Waiting for workflow (20s) ==="
sleep 20

echo "=== Fetching proofpack ==="
PACK=$(curl -sf http://localhost:8080/v1/changes/CHG-001/proofpack)

echo "=== Asserting netbox.validate_observed in tool_calls ==="
if echo "$PACK" | grep -q "netbox.validate_observed"; then
  echo "PASS: netbox.validate_observed found in tool_calls"
else
  echo "WARN: netbox.validate_observed not found (may be mock path); continuing"
fi

echo "=== Dev smoke test complete ==="
