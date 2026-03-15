# Contributing to InfraSentinel

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker & Docker Compose (for full-stack runs)

## Setup

```bash
git clone https://github.com/your-org/InfraSentinel.git
cd InfraSentinel
uv sync --extra dev
```

## Running Locally

### Mock mode (no external accounts)

```bash
# Start Temporal + Postgres + MinIO + API + Worker
make docker-up

# Or run API + Worker directly (requires Temporal/Postgres/MinIO running)
make up   # starts API and worker
make mcp  # starts MCP servers (camera, cv, netbox, ticketing)
```

### Dev mode (with NetBox)

```bash
make docker-dev   # adds NetBox + Redis + Postgres for NetBox
make seed-netbox  # seed NetBox with sample devices/ports/cables
```

### Environment

- Copy `infra/env/.env.mock.example` to `.env` for mock mode.
- Copy `infra/env/.env.dev.example` to `.env` for dev mode with NetBox.

## Testing

```bash
uv run pytest -q
uv run ruff check .
uv run mypy apps packages services a2a tests
```

### Smoke tests

```bash
# Mock mode end-to-end (brings up stack, runs scenario A, asserts S2 VERIFIED)
./scripts/smoke/run_smoke.sh

# Dev mode (NetBox profile, seed, run flow)
./scripts/smoke/run_dev_smoke.sh
```

On Windows, use Git Bash or WSL to run the shell scripts.

## Adding Tools

1. Define tool schema in `packages/mcp/schemas.py`.
2. Implement handler in `services/mcp_*/handlers.py` (or equivalent).
3. Add unit tests in `tests/` for the handler.
4. Update workflow tests if the tool affects change execution.

## Workflow Changes

- Keep orchestration deterministic; push I/O into activities.
- Add/update tests in `tests/test_workflow_*.py`.
- Use `samples/` fixtures for deterministic mock scenarios.

## Code Style

- Python 3.11+ only.
- Use Pydantic models for request/response payloads.
- MCP stdio servers: log to stderr only, never stdout.
