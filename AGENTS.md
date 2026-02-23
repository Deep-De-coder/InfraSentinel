# AGENTS.md

Guidance for coding agents working in this repository.

## Conventions

- Python 3.11+ only.
- Prefer explicit, typed Pydantic models for request/response payloads.
- Keep workflow orchestration deterministic; push I/O into activities.
- Use `INFRASENTINEL_MODE=mock` as default development mode.
- Never log sensitive credentials.
- MCP stdio servers must not write operational logs to stdout.

## Repo Layout

- Add domain contracts in `packages/core/`.
- Add decision logic in `packages/agents/`.
- Add tool schema + wrappers in `packages/mcp/`.
- Add external tool adapters in `services/mcp_*/`.
- Add API endpoints in `apps/api/`.
- Add Temporal logic in `apps/worker/`.
- Add tests in `tests/` with deterministic fixtures.

## Tooling

- Install: `uv sync`
- Lint: `uv run ruff check .`
- Type check: `uv run mypy apps packages services a2a tests`
- Test: `uv run pytest -q`

## Tests

- For each new tool handler, add a unit test in `tests/`.
- For workflow changes, update/add workflow tests for happy and blocked paths.
- Keep tests deterministic in mock mode using `samples/` fixture data.

## MCP Notes

- Place shared tool schemas in `packages/mcp/schemas.py`.
- Keep server handlers pure and deterministic when `mock` mode is enabled.
- Ensure stderr-only logging for stdio transport servers.
