# Marquise

<!-- TODO: add screenshot / demo gif here -->

Montreal cinema showtimes — aggregated, normalized, and queryable.

Marquise fetches showtime data from multiple theater chains and independent cinemas across Montreal, normalizes it into a unified PostgreSQL schema, and exposes it through a CLI and a read-only REST API (live at [`https://marquise-api.fly.dev`](https://marquise-api.fly.dev/docs)).

---

## Features

- Aggregates showtimes from six sources: **Cineplex**, **CinemaCinema**, **Cinema Public**, **Cinémathèque québécoise**, **Cinéma Moderne**, and **Théâtre Outremont**
- Enriches movie records with metadata (poster, cast, directors, genres, runtime) fetched from each source's detail pages
- Source-to-cinema assignments are stored in the database — adding a new cinema is a DB write, not a code change
- Read-only REST API (FastAPI) with pagination, in-memory caching, rate limiting, and configurable CORS — deployed on Fly.io
- Clean Architecture: strict inward-only dependency rule across domain → application → interface adapters → infrastructure
- Async throughout (asyncpg + asyncio), single CLI entrypoint via Typer + Rich

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Package manager | uv |
| Database | Supabase (PostgreSQL via asyncpg) |
| CLI | Typer + Rich |
| REST API | FastAPI (deployed on Fly.io) |
| Testing | pytest + pytest-asyncio |
| Linting / formatting | Ruff |
| Type checking | ty |

## Live API

The read-only REST API is deployed and publicly reachable at `https://marquise-api.fly.dev`:

- [`https://marquise-api.fly.dev/docs`](https://marquise-api.fly.dev/docs) — interactive OpenAPI (Swagger) UI
- [`https://marquise-api.fly.dev/health`](https://marquise-api.fly.dev/health) — liveness probe

See [docs/api.md](docs/api.md) for the full endpoint reference.

## Installation

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ArnaudJalbert/marquise.git
cd marquise
uv sync
```

Configure environment variables:

```bash
cp .env.example .env
make cli --help
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (`postgresql://...`) |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Supabase anon/publishable key |
| `CINEPLEX_API_KEY` | No | Cineplex API subscription key (`Ocp-Apim-Subscription-Key`) |
| `DATABASE_SCHEMA` | No | Schema name (default: `marquise`) |
| `MARQUISE_API_CACHE_TTL_SECONDS` | No | Read-only API in-memory response cache TTL, in seconds (default: `3600`) |
| `MARQUISE_API_CORS_ORIGINS` | No | Comma-separated list of allowed CORS origins for the read-only API (default: empty — no cross-origin requests permitted) |
| `MARQUISE_API_RATE_LIMIT` | No | Per-client rate limit for the read-only API (see [docs/api.md](docs/api.md#rate-limiting)) |
| `MARQUISE_API_LOG_LEVEL` | No | Log level for the API server |
| `MARQUISE_EMAIL` / `MARQUISE_PASSWORD` | No | Credentials used by `marquise auth` to authenticate against Supabase |

See the [Supabase setup guide](docs/setup/supabase-cinema-table.md) to initialize the database schema.

## Makefile (Common Tasks)

```bash
make cli         # launch the CLI
make api         # launch the API server (hot-reload)
make test        # run all test suites
make lint        # ruff check
make format      # ruff format
make ty          # type check marquise-core
```

See the full commands reference in [AGENTS.md](AGENTS.md#7-commands-reference) or [CONTRIBUTING.md](CONTRIBUTING.md).

## CLI

```bash
make cli --help
```

### Import showtimes

```bash
# Interactive: pick a cinema, then a date range
make cli source import

# Non-interactive: import for every cinema that has a source assignment
make cli import all
```

### Manage sources and cinemas

Most management commands are interactive — they prompt for the cinema/source rather than taking flags.

```bash
# Register sources from the code registry into the database (admin only)
make cli source register

# Assign a registered source to a cinema (interactive selection)
make cli source assign

# List sources registered in the database
make cli source list-registered

# List sources available in the code-level registry
make cli source list-available

# Show which source is assigned to each cinema
make cli source list-assignments

# Create / list cinemas
make cli cinema create
make cli cinema list
```

## REST API

Start the server locally:

```bash
make api
# → http://localhost:8000/docs   (interactive OpenAPI UI)
# → http://localhost:8000/health (liveness probe)
```

A production instance is live at [`https://marquise-api.fly.dev`](https://marquise-api.fly.dev/docs). See [docs/api.md](docs/api.md) for the full endpoint reference, pagination, caching, rate limiting, and CORS configuration.

## Documentation

| | |
|---|---|
| [Architecture](docs/architecture.md) | Layer diagram, key patterns, data flow |
| [Sources](docs/sources.md) | Scraper internals, adding a new source |
| [Setup](docs/setup/supabase-cinema-table.md) | Database initialization |
| [Contributing](CONTRIBUTING.md) | Dev setup, commands, CI, conventions |
