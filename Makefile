.PHONY: test test-core test-api test-cli api cli lint format ty docs web-demo

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

docs:
	uv run mkdocs serve

# Start the marquise-components demo page (dev-only) → http://localhost:5173
web-demo:
	cd web && pnpm --filter marquise-components dev
