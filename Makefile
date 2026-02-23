PYTHON ?= python
UV ?= uv

.PHONY: up dev mcp test eval lint typecheck

up:
	docker compose -f infra/docker-compose.yml up -d

dev:
	$(UV) run python -m apps.api.main & $(UV) run python -m apps.worker.main

mcp:
	$(UV) run python -m services.mcp_camera.server & \
	$(UV) run python -m services.mcp_cv.server & \
	$(UV) run python -m services.mcp_netbox.server & \
	$(UV) run python -m services.mcp_ticketing.server

test:
	$(UV) run pytest -q

eval:
	npx promptfoo eval -c eval/promptfoo.yaml

lint:
	$(UV) run ruff check .

typecheck:
	$(UV) run mypy apps packages services a2a tests
