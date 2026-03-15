#!/usr/bin/env bash
# One-shot smoke test: mock mode end-to-end.
# Brings up stack, runs scenario A, asserts S2 VERIFIED.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p runtime/proofpacks

echo "=== Bringing up stack (mock) ==="
docker compose -f infra/docker-compose.yml up -d --build

echo "=== Waiting for API (up to 60s) ==="
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

echo "=== Starting change CHG-001 ==="
curl -sf -X POST http://localhost:8080/v1/changes/start \
  -H "Content-Type: application/json" \
  -d '{"change_id":"CHG-001","scenario":"CHG-001_A"}'

echo ""
echo "=== Uploading evidence S1 ==="
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S1" -F "evidence_id=EVID-001"

echo ""
echo "=== Uploading evidence S2 ==="
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S2" -F "evidence_id=EVID-002"

echo ""
echo "=== Uploading evidence S3 ==="
curl -sf -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S3" -F "evidence_id=EVID-003"

echo ""
echo "=== Waiting for workflow (15s) ==="
sleep 15

echo "=== Fetching proofpack ==="
PACK=$(curl -sf http://localhost:8080/v1/changes/CHG-001/proofpack)

echo "=== Asserting S2 VERIFIED ==="
if command -v jq >/dev/null 2>&1; then
  S2_STATUS=$(echo "$PACK" | jq -r '.steps[] | select(.step_id=="S2") | .status // empty')
else
  S2_STATUS=$(echo "$PACK" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for s in d.get('steps',[]):
  if s.get('step_id')=='S2':
    print(s.get('status',''))
    break
" 2>/dev/null || echo "")
fi
if [ "$S2_STATUS" = "verified" ]; then
  echo "PASS: S2 is VERIFIED"
else
  echo "FAIL: S2 status is '$S2_STATUS', expected verified"
  exit 1
fi

echo "=== Smoke test PASSED ==="
