#!/usr/bin/env bash
# Smoke test: NetBox dev mode end-to-end.
# Usage: ./scripts/smoke/netbox_demo.sh
# Requires: docker compose, curl, python

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Starting infra (profile dev) ==="
docker compose -f infra/docker-compose.yml --profile dev up -d

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
# Create API token first via NetBox UI or use superuser for seed
# For automation, we use the seed script (may need NETBOX_TOKEN from env)
python infra/netbox/seed_netbox.py || true

echo "=== Creating approved mapping for CHG-DEV-001 ==="
mkdir -p runtime/approved_mappings
cat > runtime/approved_mappings/CHG-DEV-001.json << 'EOF'
{
  "allowed_endpoints": [
    {"panel_id": "PANEL-A", "port_label": "24", "cable_tag": "MDF-01-R12-P24"}
  ]
}
EOF

echo "=== Starting change CHG-DEV-001 ==="
curl -s -X POST http://localhost:8080/v1/changes/start \
  -H "Content-Type: application/json" \
  -d '{"change_id":"CHG-DEV-001","scenario":"CHG-001_A"}' || true

echo "=== Uploading evidence (fixture) ==="
curl -s -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-DEV-001" \
  -F "step_id=S1" \
  -F "evidence_id=EVID-001" || true

echo "=== Fetching proofpack ==="
curl -s http://localhost:8080/v1/changes/CHG-DEV-001/proofpack | head -50

echo "=== Smoke test complete ==="
