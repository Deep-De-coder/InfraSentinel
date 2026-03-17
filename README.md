# InfraSentinel

InfraSentinel is a production-oriented, pilot-stage data-center change-safety agent. It guides technicians through Method of Procedure (MOP) steps, captures evidence (photos), validates rack/port/cable correctness against a CMDB (e.g., NetBox), blocks on mismatch or low confidence, and produces auditable proof packs. The core value: **prevent wrong cable/port changes during MOP execution** using evidence capture + CMDB validation.

---

## Problem

Data-center change execution carries operational risk: wrong cable swaps, incorrect port patching, and misidentified equipment lead to outages and compliance failures. Manual MOP compliance is error-prone; evidence is often missing or not tied to change records; and audit trails are incomplete.

InfraSentinel addresses:

- **MOP compliance** — Step-by-step guidance with evidence requirements per step
- **Wrong-cable incidents** — OCR extraction of port labels and cable tags, validated against CMDB truth
- **Evidence capture** — Quality-gated photo uploads with retake guidance when blur/glare/resolution fail
- **Auditability** — Proof packs with step outcomes, tool calls, and evidence references

---

## What the System Does Today

The working flow:

1. **Start change** — API starts a Temporal workflow with a change ID and scenario
2. **Upload evidence** — Per-step evidence (fixture ID or file) with quality gate
3. **Quality gate** — Blur, brightness, glare, resolution checks; `NEEDS_RETAKE` with guidance if failed
4. **OCR / extraction** — Port label and cable tag extraction (mock or Tesseract)
5. **NetBox validation** — Observed vs expected mapping (mock or real NetBox REST)
6. **Approval / block / retake** — Block on mismatch; approval override for BLOCKED steps; retake on low confidence
7. **Proof pack generation** — JSON proof pack with step results, tool calls, evidence IDs

---

## Architecture Overview

| Component | Role |
|-----------|------|
| **API** | FastAPI app for starting changes, uploading evidence, approving steps, fetching proof packs |
| **Temporal worker** | Durable workflows (`ChangeExecutionWorkflow`, `ChangeWorkflow`), activities for MOP/CV/CMDB |
| **MCP services** | Tool mesh: camera (capture/store), CV (OCR, quality), NetBox (validate), ticketing (change/approval) |
| **A2A services** | HTTP agents for MOP, Vision, CMDB advice; optional, advisory only |
| **Storage** | Local or MinIO for evidence; Postgres (or SQLite in mock) for step results and audit events |
| **NetBox** | DCIM/CMDB for port/cable validation; mock mode uses fixtures |

**Repo layout:**

- `apps/api/` — FastAPI API
- `apps/worker/` — Temporal worker and workflows
- `packages/core/` — Config, models, DB, storage, logic, fixtures
- `packages/agents/` — MOP, Vision, CMDB agents + LLM wiring
- `packages/mcp/` — MCP tool schemas and client
- `packages/cv/` — OCR pipeline, parsing, quality
- `packages/a2a/` — A2A message schema and HTTP client
- `services/mcp_*` — MCP servers (camera, cv, netbox, ticketing)
- `services/a2a_*_agent/` — A2A agent services
- `infra/` — Docker Compose, env configs

---

## Current Implementation Status

| Area | Status | Notes |
|------|--------|-------|
| **Core** | Implemented | Config, models, storage, DB, logic, fixtures, runtime |
| **API** | Implemented | All endpoints wired and working |
| **Worker** | Implemented | Both workflows, all activities |
| **Agents** | Implemented | MOP, Vision, CMDB, LLM (mock/Anthropic/LiteLLM) |
| **A2A services** | Implemented | MOP, Vision, CMDB agents with agent cards |
| **MCP CV** | Partial | Mock + Tesseract; `CV_MODE=mock` or `CV_MODE=tesseract` |
| **MCP NetBox** | Partial | Mock + real; `NETBOX_MODE=mock` or `NETBOX_MODE=netbox` |
| **MCP Camera** | Mock-only | Reads from file path or base64; no real camera hardware |
| **MCP Ticketing** | Mock-only | Fixture-based; writes to `runtime/ticketing_log.json` |
| **Observability** | Skeleton | Tracer provider set; OTLP/Langfuse hooks are placeholders |
| **Infra** | Implemented | Docker Compose, env configs, dev profile |
| **Tests** | Partial | 18+ test files; no full API→workflow E2E, no MCP stdio coverage |

---

## What Is Fully Working

- **Core packages** — Config, models, storage (local + MinIO), DB, state machine, proofpack logic, fixtures
- **API** — `/healthz`, `/v1/changes/start`, `/v1/evidence/upload`, `/v1/changes/{id}/approve`, step prompt, step result, proofpack, evidence URL
- **Worker** — `ChangeExecutionWorkflow` and `ChangeWorkflow` with evidence signals, quality gate, CV extract, CMDB validate, approval override
- **Agents** — MOP, Vision, CMDB advice; LLM providers (mock, Anthropic, LiteLLM)
- **CV pipeline** — OCR (mock + Tesseract), port/cable parsing, quality metrics, retake guidance
- **A2A agents** — MOP, Vision, CMDB HTTP services with agent cards
- **Infra** — Docker Compose stack (Temporal, Postgres, MinIO, API, Worker, MCP servers, A2A agents); dev profile with NetBox

---

## What Is Partially Implemented

- **MCP CV** — Mock mode uses fixtures; Tesseract mode uses real OCR. Crop hints optional.
- **MCP NetBox** — Mock mode uses fixtures; NetBox mode uses REST API. Adapter layer is skeleton.
- **Vision quality** — `quality.py` implemented; `vision/` package init is minimal.
- **Tests** — Unit and workflow tests exist; full API→workflow E2E and MCP stdio transport not covered.

---

## What Is Still Mock / Not Production-Ready

- **MCP Camera** — No real camera; reads from file path or base64 only
- **MCP Ticketing** — Fixture-based; `post_step_result` and `request_approval` write to local JSON
- **Observability** — OTLP and Langfuse hooks are `pass` placeholders
- **Adapters** — NetBox, ticketing, and CV adapters are marked as skeletons in code
- **Root `a2a/server.py`** — Legacy placeholder; real A2A agents live in `services/a2a_*_agent/`

---

## Running the Project

### Prerequisites

| Tool | Purpose |
|------|---------|
| Docker Desktop | Temporal, Postgres, MinIO, NetBox (dev) |
| Python 3.11+ | API, worker, tests |
| uv (recommended) | Python dependency management |
| jq | Smoke test JSON parsing |

```bash
# Verify
docker compose version
python --version   # 3.11+
uv sync --extra dev && make test
```

### Mock Mode (no external keys)

Uses `infra/env/.env.mock`. No API keys required.

**Quickstart:**

```bash
bash scripts/dev/mock_quickstart.sh
```

**Manual:**

```bash
make docker-up
bash scripts/smoke/run_smoke.sh
```

### Dev Mode with NetBox

Uses `infra/env/.env.dev` (git-ignored). Requires NetBox token for real validation.

**With Claude (Anthropic API key):**

```bash
bash scripts/dev/dev_quickstart_claude.sh
```

**Manual:**

```bash
# 1. Create infra/env/.env.dev (copy from .env.dev.example)
# 2. Start stack with dev profile
docker compose -f infra/docker-compose.yml --profile dev up -d

# 3. Wait for NetBox (~2 min), create token in UI (admin/admin)
# 4. Seed NetBox
NETBOX_URL=http://localhost:8001 NETBOX_TOKEN=your-token uv run python infra/netbox/seed_netbox.py

# 5. Run smoke test
bash scripts/smoke/run_dev_smoke.sh
```

**Note:** Camera and ticketing remain mock-only in all modes.

### Quickstart (API + Worker locally)

```bash
make up          # or make docker-up
uv sync
make dev         # API + worker
make mcp        # MCP servers (separate terminal)
```

**Start change and upload evidence:**

```bash
# Start change (add -H "X-INFRA-KEY: $key" if INFRA_API_KEY is set)
curl -X POST http://localhost:8080/v1/changes/start \
  -H "Content-Type: application/json" \
  -d '{"change_id":"CHG-001","scenario":"CHG-001_A"}'

# Upload evidence (fixture IDs)
curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S1" -F "evidence_id=EVID-001"
curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S2" -F "evidence_id=EVID-002"
curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S3" -F "evidence_id=EVID-003"

# Fetch proof pack
curl http://localhost:8080/v1/changes/CHG-001/proofpack
```

**Approve override (if BLOCKED):**

```bash
curl -X POST http://localhost:8080/v1/changes/CHG-001/approve \
  -H "Content-Type: application/json" \
  -d '{"step_id":"S2","approver":"admin"}'
```

### Evidence Quality Gate

Before OCR/CMDB, images are checked for blur, brightness, glare, and resolution. Failed checks return `NEEDS_RETAKE` with guidance.

**Thresholds** (env): `QUALITY_BLUR_MIN=120`, `QUALITY_BRIGHTNESS_MIN=60`, `QUALITY_GLARE_MAX=0.08`, `QUALITY_MIN_W=800`, `QUALITY_MIN_H=600`.

**Example — blurry evidence:**

```bash
curl -X POST http://localhost:8080/v1/evidence/upload \
  -F "change_id=CHG-001" -F "step_id=S1" -F "evidence_id=EVID-002-BADQUALITY"
# Response: {"status":"needs_retake","guidance":[...],"quality":{...}}
```

### Scenario Fixtures

| Scenario | Behavior |
|----------|----------|
| **CHG-001_A** | Happy path; all evidence matches expected mapping |
| **CHG-001_B** | S2 wrong port (99 vs 24) → BLOCKED, requires approval |
| **CHG-001_C** | S2 low confidence → NEEDS_RETAKE; upload EVID-002-RETAKE to proceed |

---

## Testing

**Run tests:**

```bash
make test
# or: uv run pytest -q
```

**Coverage:** 18+ test files for auth, A2A, agents, CV parsing/quality, MCP tools, state machine, workflows, scenarios.

**Not yet covered:** Full API→workflow E2E, MCP stdio transport, observability.

**Optional OCR:** Install `pytesseract` and system `tesseract`, set `CV_MODE=tesseract`.

---

## Known Limitations

- **No real ticketing integration** — Ticketing writes to local JSON only
- **No real camera hardware** — Camera MCP reads from file/base64
- **Limited real OCR path** — Tesseract works; no cloud/GPU OCR yet
- **No production observability** — OTLP/Langfuse hooks are placeholders
- **Missing full E2E coverage** — API→workflow integration tests not yet in place

---

## Next Milestones

1. **Stabilize full E2E flow** — Add API→workflow integration tests
2. **Real ticketing adapter** — Integrate with ServiceNow, Jira, or similar
3. **Real observability** — Wire OTLP exporter and optional Langfuse
4. **Better CV backend** — Cloud OCR or GPU-based extraction
5. **Real camera ingestion** — Hardware camera or mobile app capture
6. **Broader E2E tests** — MCP stdio, full change lifecycle

---

## Technical Stack

| Layer | Technologies |
|-------|--------------|
| Runtime | Python 3.11+, FastAPI, Uvicorn |
| Orchestration | Temporal |
| Database | SQLAlchemy (async), Postgres, SQLite (mock) |
| Storage | MinIO (S3-compatible), local filesystem |
| DCIM/CMDB | NetBox |
| Tool mesh | MCP (FastMCP) |
| Agents | A2A HTTP, Anthropic Claude, LiteLLM |
| OCR | Tesseract (optional), mock fixtures |
| Infra | Docker Compose |

---

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `INFRASENTINEL_MODE` | `mock` (default) or `prod` |
| `INFRA_API_KEY` | If set, write endpoints require `X-INFRA-KEY` header |
| `AUTH_READS` | Require auth for read endpoints |
| `EVIDENCE_BACKEND` | `local` or `minio` |
| `NETBOX_MODE` | `mock` or `netbox` |
| `CV_MODE` | `mock` or `tesseract` |
| `A2A_MODE` | `off` or `http` |
| `LLM_PROVIDER` | `mock`, `anthropic`, or `litellm` |
| `ANTHROPIC_API_KEY` | For Claude |

See `infra/env/.env.mock.example` and `infra/env/.env.dev.example` for full lists.

---

## Development Notes

- MCP stdio servers must not write logs to stdout; use stderr only
- Temporal workflow logic is deterministic; I/O lives in activities
- Step outcomes are persisted with audit events for traceability
- False-green rate is a key safety metric: low-confidence CV should block and request retake
