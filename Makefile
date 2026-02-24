PYTHON ?= python
UV ?= uv

.PHONY: up dev mcp test eval lint typecheck data-help synth cv-test

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
