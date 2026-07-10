# Marquise

Montreal cinema showtimes — aggregated, normalized, and queryable.

Marquise scrapes showtime data from multiple theater chains and independent cinemas across Montreal, normalizes it into a unified schema, and stores it in a PostgreSQL database. It ships as a CLI for data management and a read-only REST API for querying.

## What's in here

| Section | What you'll find |
|---|---|
| [Architecture](architecture.md) | Layer diagram, key patterns, data flow |
| [API](api.md) | REST API — endpoints, CORS, caching, rate limiting |
| [Sources](sources.md) | How scrapers and adapters work, adding a new source |
| [Setup → Supabase](setup/supabase-cinema-table.md) | Database setup guide |
| [Contributing](https://github.com/ArnaudJalbert/marquise/blob/main/CONTRIBUTING.md) | Dev setup, commands, CI, conventions |

## Quick Start

```bash
git clone https://github.com/ArnaudJalbert/marquise.git
cd marquise
uv sync
cp .env.example .env   # fill in SUPABASE_URL, SUPABASE_KEY, DATABASE_URL
uv run marquise --help
```

## Read-Only REST API

Marquise ships a read-only FastAPI with pagination, in-memory caching, and configurable CORS:

```bash
# Start the API server
uv run marquise api
# → http://localhost:8000/docs (OpenAPI UI)
# → http://localhost:8000/health
```

Endpoints: `GET /cinemas`, `GET /cinemas/{id}/showtimes`, `GET /movies/{id}`.

See the [API docs](api.md) for details, including how to configure CORS origins, cache TTL, and rate limiting.

## Supported Sources

| Source | Type | Enrichment |
|--------|------|------------|
| Cineplex | API + web | Yes |
| CinemaCinema | SvelteKit API | Yes |
| Cinema Public | HTML scraping | Yes |
| Cinémathèque québécoise | HTML scraping | Yes |
| Cinéma Moderne | HTML scraping | Yes |

## Roadmap

- Admin CRUD API endpoints
- Authentication for write operations
- Additional Montreal cinema sources
