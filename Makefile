.PHONY: test test-core test-core-integrations test-api test-cli api cli lint format ty deploy-api deploy-interface web web-live web-demo

test: test-core test-api test-cli

test-core:
	uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/ -q

test-core-integrations:
	uv run --package marquise-core pytest packages/marquise-core/tests/integration_tests/ -q

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

deploy-api:
	flyctl deploy . --config apps/marquise-api/fly.toml --remote-only

deploy-interface:
	cd web && flyctl deploy . --config apps/marquise-interface/fly.toml --remote-only

# Start the marquise-components sample-data demo (dev-only) → http://localhost:5173
web-demo:
	cd web && pnpm prototype

# Start the interface → http://localhost:5173 (/v1 proxies to a local API on :8000; run `make api`)
web:
	cd web && pnpm --filter marquise-interface dev

# Start the local API and the interface → http://localhost:5173
# (requires the DATABASE_URL env var, e.g. via the repo's .env file)
web-live:
	@echo "Starting local API on http://localhost:8000 ..."; \
	uv run --package marquise-api uvicorn marquise_api.app:create_app --factory --host 0.0.0.0 --port 8000 & \
	API_PID=$$!; \
	trap 'kill $$API_PID 2>/dev/null' EXIT INT TERM; \
	cd web && pnpm --filter marquise-interface dev

# Isolated real API + Postgres + built React app. Never load a project .env.
LOCAL_COMPOSE = docker compose --env-file /dev/null --project-name marquise-local -f compose.local.yml

.PHONY: local-up local-down local-logs local-seed local-status
local-up:
	$(LOCAL_COMPOSE) up --build -d --wait
	$(MAKE) local-seed

local-down:
	$(LOCAL_COMPOSE) down

local-logs:
	$(LOCAL_COMPOSE) logs --tail=100 -f

local-status:
	$(LOCAL_COMPOSE) ps

# Replace only the generated local screenings; retain non-fixture rows.
local-seed:
	$(LOCAL_COMPOSE) exec -T db psql -v ON_ERROR_STOP=1 -U marquise_local -d marquise_local < local/seed.sql
