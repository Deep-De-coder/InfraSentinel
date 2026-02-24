# InfraSentinel

Production-grade, cloud-agnostic monorepo scaffold for durable MOP guidance and verification.

InfraSentinel guides data-center technicians through change steps, verifies rack/port/cable correctness using evidence + CMDB truth, blocks on mismatch/low confidence, and produces auditable proof packs.

## Architecture

- `apps/api/`: FastAPI API for starting workflows and uploading evidence.
- `apps/worker/`: Temporal worker hosting durable workflows and activities.
- `packages/core/`: Typed domain models, config, DB schema, storage interfaces.
- `packages/agents/`: Typed decision agents (PydanticAI-compatible wrappers).
- `packages/mcp/`: Shared MCP tool schemas and client abstraction.
- `services/mcp_*`: MCP tool servers (camera, cv, netbox, ticketing).
- `a2a/`: Agent-to-agent placeholder (`agent_card.json`, minimal HTTP endpoints).
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

## Scenario Fixtures

- **CHG-001_A**: Happy path, all evidence IDs match expected mapping.
- **CHG-001_B**: S2 has wrong port (99 vs 24) => BLOCKED, requires approval.
- **CHG-001_C**: S2 first upload has low confidence => NEEDS_RETAKE; upload EVID-002-RETAKE to proceed.

## Development Notes

- MCP stdio servers must never write logs to stdout; all logs go to stderr.
- Temporal workflow logic is deterministic and orchestration-first.
- Step outcomes are persisted with audit events for traceability.
- False-Green Rate is a key safety metric: low-confidence CV outputs should block progression and request retake.