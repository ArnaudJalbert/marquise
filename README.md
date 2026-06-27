# Marquise

<!-- TODO: add screenshot / demo gif here -->

Montreal cinema showtimes — aggregated, normalized, and queryable.

Marquise fetches showtime data from multiple theater chains and independent cinemas across Montreal, normalizes it into a unified PostgreSQL schema, and exposes it through a CLI. A read-only REST API is planned.

---

## Features

- Aggregates showtimes from **Cineplex**, **CinemaCinema**, and **Cinema Public**
- Enriches movie records with metadata (poster, cast, directors, genres, runtime) fetched from each source's detail pages
- Source-to-cinema assignments are stored in the database — adding a new cinema is a DB write, not a code change
- Clean Architecture: strict inward-only dependency rule across domain → application → interface adapters → infrastructure
- Async throughout (asyncpg + asyncio), single CLI entrypoint via Typer + Rich

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Package manager | uv |
| Database | Supabase (PostgreSQL via asyncpg) |
| CLI | Typer + Rich |
| Testing | pytest + pytest-asyncio |
| Linting / formatting | Ruff |
| Type checking | ty |

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
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (`postgresql://...`) |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Supabase anon/publishable key |
| `CINEPLEX_API_KEY` | No | Cineplex API subscription key (`Ocp-Apim-Subscription-Key`) |
| `DATABASE_SCHEMA` | No | Schema name (default: `marquise`) |

See the [Supabase setup guide](https://arnaudjalbert.github.io/marquise/setup/supabase-cinema-table/) to initialize the database schema.

## CLI Usage

```bash
uv run marquise --help
```

### Import showtimes

```bash
uv run marquise source import \
  --cinema-id <cinema-uuid> \
  --start-date 2026-06-27 \
  --end-date 2026-06-27
```

### Manage sources and cinemas

```bash
# Register a source definition
uv run marquise source create --name cineplex --display-name "Cineplex"

# Assign a source to a cinema
uv run marquise source assign \
  --cinema-id <cinema-uuid> \
  --source-name cineplex

# List sources
uv run marquise source list

# List cinemas
uv run marquise cinema list
```

## Documentation

Full docs at [arnaudjalbert.github.io/marquise](https://arnaudjalbert.github.io/marquise/).

| | |
|---|---|
| [Architecture](https://arnaudjalbert.github.io/marquise/architecture/) | Layer diagram, key patterns, data flow |
| [Sources](https://arnaudjalbert.github.io/marquise/sources/) | Scraper internals, adding a new source |
| [Setup](https://arnaudjalbert.github.io/marquise/setup/supabase-cinema-table/) | Database initialization |
| [Contributing](CONTRIBUTING.md) | Dev setup, commands, CI, conventions |
