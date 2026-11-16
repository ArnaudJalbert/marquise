# Local stack on a copy of production. Recipes load `.env.local` only;
# `copy-prod-db` alone reads `.env`, as the source of the dump.

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
    trap 'trap - EXIT INT TERM; kill 0' EXIT INT TERM
    {{ api_reload }} &
    {{ vite_reload }} &
    wait

# Replace the local marquise schema with a pg_dump of production
copy-prod-db:
    case "$DATABASE_URL" in \
        *@localhost:*|*@localhost/*|*@127.0.0.1:*|*@127.0.0.1/*|*@db:*|*@db/*) ;; \
        *) echo "Refusing: .env.local DATABASE_URL is not local." >&2; exit 1 ;; \
    esac
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
