# Project commands and the local stack on a copy of production. Recipes load
# `.env.local` only; `copy-prod-db` alone reads `.env`, as the source of the dump.

set dotenv-filename := ".env.local"
set dotenv-override

compose := "docker compose --env-file .env.local"
psql := compose + " exec -T db psql -v ON_ERROR_STOP=1 -U marquise -d marquise"

# Start postgres; fails until `just copy-prod-db` has filled it
start-db:
    {{ compose }} up -d --wait db
    if [ -z "$({{ psql }} -Atc "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'marquise'")" ]; then \
        echo "No production copy found. Run: just copy-prod-db" >&2; exit 1; \
    fi

api_reload := "uv run uvicorn marquise_api.app:create_app --factory --port 18000 --reload --reload-dir apps/marquise-api/src --reload-dir packages/marquise-core/src"
vite_reload := "pnpm --dir web --filter marquise-interface dev --port 15173 --strictPort"

# Start postgres and the API image
start-api: start-db
    {{ compose }} up -d --build --wait api

# Start the API and interface images: the whole app on the copy
start-local-stack: start-api
    {{ compose }} up -d --build --wait interface
    @echo "Interface: http://localhost:15173"

# Run Vite with hot reload against the API image
start-interface-reload: start-api
    {{ compose }} stop interface
    {{ vite_reload }}

# Run uvicorn with reload on the host against the local copy
start-api-reload: start-db
    {{ compose }} stop api
    {{ api_reload }}

# Run uvicorn and Vite with reload together; Ctrl-C stops both, postgres keeps running
start-local-stack-reload: start-db
    #!/usr/bin/env bash
    set -euo pipefail
    {{ compose }} stop api interface
    # Ignore Ctrl-C while forking, then trap: a child that inherits a trap can swallow the TERM.
    trap '' INT
    {{ api_reload }} & api=$!
    {{ vite_reload }} & vite=$!
    trap 'trap "" INT TERM; kill 0' EXIT
    trap 'exit 130' INT TERM
    # When either half exits, stop the other (macOS bash 3.2 has no `wait -n`).
    while kill -0 "$api" 2>/dev/null && kill -0 "$vite" 2>/dev/null; do sleep 1; done
    exit 1

# Replace the local marquise schema with a pg_dump of production
copy-prod-db:
    case "$DATABASE_URL" in \
        *@localhost:*|*@localhost/*|*@127.0.0.1:*|*@127.0.0.1/*|*@db:*|*@db/*) ;; \
        *) echo "Refusing: .env.local DATABASE_URL is not local." >&2; exit 1 ;; \
    esac
    [ -f .env ] || { echo "No .env found: copy-prod-db reads the production DATABASE_URL from it." >&2; exit 1; }
    {{ compose }} up -d --wait db
    PROD_DATABASE_URL="$(sed -n 's/^DATABASE_URL=//p' .env | tr -d "\"'")" \
        {{ compose }} exec -T -e PROD_DATABASE_URL db \
        sh -c ': "${PROD_DATABASE_URL:?is empty: set DATABASE_URL in .env}"; pg_dump "$PROD_DATABASE_URL" --schema=marquise --no-owner --no-privileges -f /tmp/marquise.sql'
    {{ psql }} --single-transaction -c 'DROP SCHEMA IF EXISTS marquise CASCADE' -f /tmp/marquise.sql >/dev/null
    {{ compose }} exec -T db rm /tmp/marquise.sql
    {{ psql }} -c 'SELECT (SELECT count(*) FROM marquise.movies) AS movies, (SELECT count(*) FROM marquise.screenings) AS screenings'

# Stop all services, keep the data
stop-stack:
    {{ compose }} stop

# Stop postgres and delete its volume
destroy-local-db:
    {{ compose }} down --volumes db

# Core, API and CLI test suites
test: test-core test-api test-cli

# Core unit tests
test-core:
    uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/ -q

# Core integration tests on a fresh marquise_test database in the local postgres
test-core-integrations: _reset-integration-db (_refuse-marquise-schema "postgresql://marquise:marquise@localhost:55432/marquise_test")
    DATABASE_URL="postgresql://marquise:marquise@localhost:55432/marquise_test" TMDB_API_KEY="test-only" uv run pytest integration_tests/ -q

# Start postgres and recreate marquise_test empty; literal names, so no override can reach the copy
_reset-integration-db:
    {{ compose }} up -d --wait db
    {{ compose }} exec -T db psql -v ON_ERROR_STOP=1 -U marquise -d postgres \
        -c "DROP DATABASE IF EXISTS marquise_test WITH (FORCE)" \
        -c "CREATE DATABASE marquise_test"

# Connect as the tests do and fail if the database holds the marquise schema (the copy or production)
_refuse-marquise-schema $DISPOSABLE_DATABASE_URL:
    #!/usr/bin/env -S uv run python
    import asyncio, os, sys
    from urllib.parse import unquote

    import asyncpg
    from marquise.infrastructure.postgres.database import sanitize_dsn

    url = os.environ["DISPOSABLE_DATABASE_URL"]

    async def holds_marquise_schema() -> bool:
        conn = await asyncpg.connect(sanitize_dsn(url))
        try:
            return await conn.fetchval("SELECT to_regnamespace('marquise') IS NOT NULL")
        finally:
            await conn.close()

    # The check covers one host, so refuse anything that can resolve to several.
    decoded = unquote(url) + os.environ.get("PGHOST", "")
    if "," in decoded or "service=" in decoded or "PGSERVICE" in os.environ:
        sys.exit("Refusing: use a single-host URL without a service.")
    try:
        holds_schema = asyncio.run(holds_marquise_schema())
    except Exception:
        # The error may quote connection settings, passwords included.
        sys.exit("Refusing: could not check the database.")
    if holds_schema:
        sys.exit("Refusing: this database holds the marquise schema, so it is not disposable.")

# API tests
test-api:
    uv run --package marquise-api pytest apps/marquise-api/tests -q

# CLI tests
test-cli:
    uv run --package marquise-cli pytest apps/marquise-cli/tests -q

# Run the CLI against the local copy
[positional-arguments]
cli *args:
    uv run --package marquise-cli marquise "$@"

# ruff check
lint:
    uv run ruff check .

# ruff format
format:
    uv run ruff format .

# Type check marquise-core
ty:
    uv run ty check packages/marquise-core/src

# Fly deploy, also run by CI
deploy-api:
    flyctl deploy . --config apps/marquise-api/fly.toml --remote-only

# Fly deploy, also run by CI
deploy-interface:
    cd web && flyctl deploy . --config apps/marquise-interface/fly.toml --remote-only
