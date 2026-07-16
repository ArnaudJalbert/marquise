.PHONY: test test-core test-api test-cli test-web api cli lint format ty docs web web-live web-live-remote web-admin

test: test-core test-api test-cli test-web

test-core:
	uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/ -q

test-api:
	uv run --package marquise-api pytest apps/marquise-api/tests -q

test-cli:
	uv run --package marquise-cli pytest apps/marquise-cli/tests -q

test-web:
	cd web && pnpm --filter @marquise/components test && pnpm --filter @marquise/api-client test

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

web:
	cd web && pnpm --filter marquise-interface dev

web-live:
	@trap 'kill 0' EXIT INT TERM; \
	MARQUISE_API_CORS_ORIGINS=http://localhost:5173 uv run --package marquise-api uvicorn marquise_api.app:create_app --factory --reload --host 0.0.0.0 --port 8000 & \
	(cd web && pnpm --filter marquise-interface dev:live) & \
	wait

web-live-remote:
	cd web && pnpm --filter marquise-interface dev:live:remote

web-admin:
	cd web && pnpm --filter marquise-admin dev
