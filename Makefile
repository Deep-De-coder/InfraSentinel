PYTHON ?= python
UV ?= uv
COMPOSE ?= docker compose -f infra/docker-compose.yml

.PHONY: up dev mcp test eval lint typecheck data-help synth cv-test
.PHONY: docker-up docker-dev docker-down logs seed-netbox

up:
	$(COMPOSE) up -d

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

data-help:
	@echo "See data/README.md and scripts/data/*.md for dataset instructions."
	@echo "Generate synthetic data: make synth"

synth:
	$(UV) run python scripts/data/generate_synth_patchpanel.py --n 200 --ports 24

cv-test:
	$(UV) run pytest -q tests/test_cv_parsing.py tests/test_cv_quality.py tests/test_mcp_cv_tools.py

lint:
	$(UV) run ruff check .

typecheck:
	$(UV) run mypy apps packages services a2a tests

# Docker full stack (uses infra/env/.env.mock; creates it from example if missing)
docker-up:
	@$(PYTHON) scripts/dev/ensure_env_mock.py || true
	$(COMPOSE) --env-file infra/env/.env.mock up -d --build
	@echo ""
	@echo "=== Key service URLs ==="
	@echo "  API:           http://localhost:8080"
	@echo "  Temporal UI:   http://localhost:8088"
	@echo "  MinIO console: http://localhost:9001"
	@echo ""

docker-dev:
	$(COMPOSE) --env-file infra/env/.env.mock --profile dev up -d --build

docker-down:
	$(COMPOSE) --profile dev down

logs:
	$(COMPOSE) logs -f

seed-netbox:
	NETBOX_URL=$${NETBOX_URL:-http://localhost:8001} NETBOX_TOKEN=$${NETBOX_TOKEN} python infra/netbox/seed_netbox.py
