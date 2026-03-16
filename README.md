# InfraSentinel

Production-grade, cloud-agnostic monorepo scaffold for durable MOP guidance and verification.

InfraSentinel guides data-center technicians through change steps, verifies rack/port/cable correctness using evidence + CMDB truth, blocks on mismatch/low confidence, and produces auditable proof packs.

## Prerequisites (no accounts needed)

Install these first so you can run mock mode:

| Tool | Purpose |
|------|---------|
| **Docker Desktop** | Runs Temporal, Postgres, MinIO, NetBox |
| **Python 3.11+** | API, worker, tests |
| **Node.js** | Required later for promptfoo eval |
| **jq** | Required for smoke test (JSON parsing) |
| **uv** (recommended) | Fast Python dependency management |

**Goal:** You should be able to run `make docker-up` and `make test` (pytest).

```bash
# Verify
docker compose version
python --version   # 3.11+
uv --version       # or: pip install uv
uv sync --extra dev && make test   # run tests
```

## Run in mock mode (no external keys, no accounts)

**Single command:**

```bash
bash scripts/dev/mock_quickstart.sh
```

This creates `infra/env/.env.mock` (with generated keys if missing), brings up the stack, and runs the smoke test.

**Manual steps:**

```bash
make docker-up
bash scripts/smoke/run_smoke.sh
```

`make docker-up` uses `infra/env/.env.mock` (create from `infra/env/.env.mock.example` if needed; the quickstart generates keys automatically). The smoke test requires **jq** (install: `brew install jq` / `apt install jq`).

On Windows, use Git Bash or WSL.

**At this point you have a working system with:**
- MOP step workflow
- Evidence upload
- Mock CV + mock NetBox validation
- Proofpack output

---

---

## Run with Claude (dev)

Requires an [Anthropic API key](https://console.anthropic.com/) with active credits.

**Single command (interactive — prompts for your API key):**

```bash
bash scripts/dev/dev_quickstart_claude.sh
```

This will:
1. Create `infra/env/.env.dev` from the example (prompts for `ANTHROPIC_API_KEY`; auto-generates `INFRA_API_KEY` and `MCP_API_KEY`).
2. Verify Claude is reachable (`claude-3-5-sonnet-latest`, 1-token ping).
3. Start the full stack with the dev env file (`make docker-up-dev`).
4. Run the smoke test (CHG-001_A, same as mock mode).
5. Check worker logs to confirm `LLM_PROVIDER=anthropic` was active.

**Manual steps:**

```bash
# 1. Create/update infra/env/.env.dev
bash scripts/dev/create_env_dev.sh

# 2. Test Claude connectivity
bash scripts/dev/test_claude.sh

# 3. Start stack (Claude-enabled)
make docker-up-dev
# or: bash scripts/dev/up_dev.sh

# 4. Smoke test
bash scripts/smoke/run_smoke.sh

# 5. Check Claude was used
bash scripts/dev/verify_claude_used.sh
```

`infra/env/.env.dev` is git-ignored and never committed.

Mock mode is unchanged and still runs with `bash scripts/dev/mock_quickstart.sh` / `make docker-up`.

---

## Architecture

- **Temporal** = durable orchestrator (workflows, signals, activities).
- **Worker** = safety gatekeeper; deterministic quality/confidence/CMDB rules stay in worker state machine.
- **A2A services** = specialized advisors (MOP, Vision, CMDB) over HTTP; interoperable, advisory only.
- **MCP servers** = tool mesh (camera, cv, netbox, ticketing).
- **Claude** = generates human-readable prompts only (tech_prompt, escalation_text); never decides accept/block.

- `apps/api/`: FastAPI API for starting workflows and uploading evidence.
- `apps/worker/`: Temporal worker hosting durable workflows and activities.
- `packages/core/`: Typed domain models, config, DB schema, storage interfaces.
- `packages/agents/`: Agent logic (mop, vision, cmdb) + LLM wiring.
- `packages/a2a/`: A2A message schema and HTTP client.
- `packages/mcp/`: Shared MCP tool schemas and client abstraction.
- `services/mcp_*`: MCP tool servers (camera, cv, netbox, ticketing).
- `services/a2a_*_agent/`: A2A agent services (MOP, Vision, CMDB).
- `infra/`: Local infrastructure via Docker Compose.
- `tests/`: Unit tests + workflow tests.
- `eval/`: Promptfoo harness for false-green focused evaluation.

## Quickstart (Local)

1. Start infra services:

```bash
make up
```

2. Install deps (Python 3.11+ and uv required):

```bash
uv sync
```

3. Run API + worker (mock mode default):

```bash
make dev
```

4. In another terminal, run MCP servers:

```bash
make mcp
```

5. Start a change with scenario (CHG-001):

```bash
curl -X POST http://localhost:8080/v1/changes/start \
  -H "Content-Type: application/json" \
  -d '{"change_id":"CHG-001","scenario":"CHG-001_A"}'
```

6. Upload evidence for each step (use fixture evidence_id or file):

```bash
# Scenario A: use fixture evidence IDs
curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" \
  -F "step_id=S1" \
  -F "evidence_id=EVID-001"

curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" \
  -F "step_id=S2" \
  -F "evidence_id=EVID-002"

curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" \
  -F "step_id=S3" \
  -F "evidence_id=EVID-003"
```

7. Fetch proof pack:

```bash
curl http://localhost:8080/v1/changes/CHG-001/proofpack
```

8. If a step is BLOCKED (e.g. scenario B), approve override:

```bash
curl -X POST http://localhost:8080/v1/changes/CHG-001/approve \
  -H "Content-Type: application/json" \
  -d '{"step_id":"S2","approver":"admin"}'
```

## Fastest Path To Working CV

1. `make up`
2. `make synth`
3. Run only CV MCP server: `uv run python -m services.mcp_cv.server`
4. Call tools with sample evidence IDs:
   - `evidence-good`
   - `evidence-low-confidence`

CV pipeline now performs: crop -> OCR -> parse -> confidence scoring -> retake guidance.

## Mock Mode vs Prod Mode

- `INFRASENTINEL_MODE=mock`:
  - deterministic tool responses from `samples/`.
  - evidence stored locally (default `./.data/evidence`).
  - no external API keys required.
- `INFRASENTINEL_MODE=prod`:
  - enable real adapters incrementally.
  - use MinIO/S3 for evidence.
  - use real NetBox/ticketing endpoints.
  - optionally use Anthropic Claude when `ANTHROPIC_API_KEY` is set.

## Key Environment Variables

- `INFRASENTINEL_MODE`: `mock` (default) or `prod`.
- `APP_HOST`: default `0.0.0.0`.
- `APP_PORT`: default `8080`.
- `TEMPORAL_ADDRESS`: default `localhost:7233`.
- `TEMPORAL_NAMESPACE`: default `default`.
- `TEMPORAL_TASK_QUEUE`: default `infrasentinel-task-queue`.
- `DATABASE_URL`: default sqlite in mock mode, otherwise Postgres URL.
- `EVIDENCE_BACKEND`: `local` (default) or `minio`.
- `LOCAL_EVIDENCE_DIR`: default `./.data/evidence`.
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`.
- `NETBOX_URL`, `NETBOX_TOKEN`.
- `NETBOX_MODE`: `mock` (default) or `netbox`. If `netbox`, use real NetBox REST API.
- `NETBOX_URL`, `NETBOX_TOKEN`: NetBox API URL and token (for netbox mode).
- `INFRA_API_KEY`: if set, write endpoints require `X-INFRA-KEY` header.
- `AUTH_READS`: `true` to require auth for read endpoints (proofpack, steps).
- `A2A_MODE`: `off` (default) or `http`. If `http`, worker calls A2A agent services.
- `A2A_MOP_URL`, `A2A_VISION_URL`, `A2A_CMDB_URL`: agent service URLs (default localhost:8091–8093).
- `ANTHROPIC_API_KEY`: if set, Claude is selected in agent runtime wiring.
- `CV_MODE`: `mock` (default) or `tesseract`.
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (optional).
- `OTEL_EXPORTER_OTLP_ENDPOINT` (optional).

## Run Tests and Eval

```bash
make test
make eval
```

`make eval` uses `npx promptfoo`, so Node.js is required for the evaluation harness.

Optional OCR backend:
- Install Python package: `uv add pytesseract`
- Install system binary: `tesseract` (must be on PATH)
- Set `CV_MODE=tesseract`

## Evidence Quality Gate

Before running OCR/CMDB validation, InfraSentinel checks image quality. If blur, brightness, glare, or resolution fail thresholds, the step is marked `NEEDS_RETAKE` and the API returns actionable guidance—no CV/CMDB calls are made.

**Thresholds** (env-configurable): `QUALITY_BLUR_MIN=120`, `QUALITY_BRIGHTNESS_MIN=60`, `QUALITY_GLARE_MAX=0.08`, `QUALITY_MIN_W=800`, `QUALITY_MIN_H=600`.

**Example: upload bad-quality evidence → receive guidance**

```bash
# Start change
curl -X POST http://localhost:8080/v1/changes/start \
  -H "Content-Type: application/json" \
  -d '{"change_id":"CHG-001","scenario":"CHG-001_A"}'

# Upload blurry evidence (e.g. EVID-002-BADQUALITY from fixtures)
curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" \
  -F "step_id=S1" \
  -F "evidence_id=EVID-002-BADQUALITY"
# Response: {"evidence_id":"EVID-002-BADQUALITY","status":"needs_retake","guidance":["Hold steady and tap to focus; avoid motion.",...],"quality":{...}}

# Retake with good evidence
curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" \
  -F "step_id=S1" \
  -F "evidence_id=EVID-001"
# Response: {"evidence_id":"EVID-001","status":"verifying"}
```

**Get step status** (including quality/guidance when `needs_retake`):

```bash
curl http://localhost:8080/v1/changes/CHG-001/steps/S1
```

**Get technician prompt** (from MOP agent):

```bash
curl http://localhost:8080/v1/changes/CHG-001/steps/S1/prompt
```

## A2A Agent Services

InfraSentinel can run with **A2A mode off** (default) or **on**:

- **A2A off**: Agent logic runs locally in the worker; no extra services. Fully deterministic, no keys.
- **A2A on**: Worker calls 3 HTTP agent services for tech prompts, vision guidance, and escalation text.

**Run with A2A off** (default):

```bash
make up
make dev
make mcp
# A2A_MODE=off (default); worker uses local mop_advice, vision_advice, cmdb_advice
```

**Run with A2A on**:

```bash
docker compose -f infra/docker-compose.yml up -d
# Start A2A agents (included in compose): a2a-mop-agent, a2a-vision-agent, a2a-cmdb-agent
# Then run API + worker with:
A2A_MODE=http A2A_MOP_URL=http://localhost:8091 A2A_VISION_URL=http://localhost:8092 A2A_CMDB_URL=http://localhost:8093 make dev
make mcp
```

Safety rules never change: the worker remains the final gatekeeper. A2A services only provide advice (guidance, prompts) and never decide accept/block.

## Dev Mode with NetBox

Run InfraSentinel against a real NetBox instance for DCIM/CMDB validation:

1. Start infra with NetBox (profile dev):

```bash
docker compose -f infra/docker-compose.yml --profile dev up -d
```

2. Wait for NetBox (~2 min), then create an API token in the NetBox UI (admin/admin).

3. Seed NetBox with sample data:

```bash
NETBOX_URL=http://localhost:8001 NETBOX_TOKEN=your-token python infra/netbox/seed_netbox.py
```

4. Set env and run API + worker:

```bash
NETBOX_MODE=netbox NETBOX_URL=http://localhost:8001 NETBOX_TOKEN=your-token make dev
make mcp
```

5. Start a change and upload evidence. The worker writes `runtime/approved_mappings/{change_id}.json` from fixtures; NetBox validates observed panel/port/cable against real DCIM data.

**Smoke test** (requires docker, API, worker running):

```bash
./scripts/smoke/netbox_demo.sh
```

## Scenario Fixtures

- **CHG-001_A**: Happy path, all evidence IDs match expected mapping.
- **CHG-001_B**: S2 has wrong port (99 vs 24) => BLOCKED, requires approval.
- **CHG-001_C**: S2 first upload has low confidence => NEEDS_RETAKE; upload EVID-002-RETAKE to proceed.

## Development Notes

- MCP stdio servers must never write logs to stdout; all logs go to stderr.
- Temporal workflow logic is deterministic and orchestration-first.
- Step outcomes are persisted with audit events for traceability.
- False-Green Rate is a key safety metric: low-confidence CV outputs should block progression and request retake.