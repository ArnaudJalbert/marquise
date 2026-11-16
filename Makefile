.PHONY: test test-core test-core-integrations test-api test-cli cli lint format ty deploy-api deploy-interface

test: test-core test-api test-cli

test-core:
	uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/ -q

test-core-integrations:
	uv run pytest integration_tests/ -q

test-api:
	uv run --package marquise-api pytest apps/marquise-api/tests -q

test-cli:
	uv run --package marquise-cli pytest apps/marquise-cli/tests -q

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
