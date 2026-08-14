.PHONY: test test-core test-api api cli lint format ty web web-live web-demo

test: test-core test-api test-cli

test-core:
	uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/ -q

test-core-integrations:
	uv run --package marquise-core pytest packages/marquise-core/tests/integrations-tests/ -q

test-api:
	uv run --package marquise-api pytest apps/marquise-api/tests -q

test-cli:
	uv run --package marquise-cli pytest apps/marquise-cli/tests -q

api:
	uv run --package marquise-api uvicorn marquise_api.app:create_app --factory --reload --host 0.0.0.0 --port 8000

cli:
	uv run --package marquise-cli marquise

lint:
	uv run ruff check .

format:
	uv run ruff format .

ty:
	uv run ty check packages/marquise-core/src

# Start the marquise-components demo page (dev-only) → http://localhost:5173
web-demo:
	cd web && pnpm --filter marquise-components dev

# Start the Marquise landing page with mock data → http://localhost:5173
web:
	cd web && VITE_MARQUISE_DATA_SOURCE=mock pnpm --filter marquise-interface dev

# Start the local API and the landing page with live data → http://localhost:5173
# (requires the DATABASE_URL env var, e.g. via the repo's .env file)
web-live:
	@echo "Starting local API on http://localhost:8000 ..."; \
	uv run --package marquise-api uvicorn marquise_api.app:create_app --factory --host 0.0.0.0 --port 8000 & \
	API_PID=$$!; \
	trap 'kill $$API_PID 2>/dev/null' EXIT INT TERM; \
	cd web && VITE_MARQUISE_DATA_SOURCE=api pnpm --filter marquise-interface dev
