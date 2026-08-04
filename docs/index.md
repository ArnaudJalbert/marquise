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
cp .env.example .env   # fill in DATABASE_URL
uv run marquise --help
```

## Read-Only REST API

Marquise ships a read-only FastAPI with pagination, in-memory caching, and configurable CORS:

```bash
# Start the API server
make api
# → http://localhost:8000/docs (OpenAPI UI)
# → http://localhost:8000/health
```

Endpoints (versioned under `/v1`) cover cinemas, movies, and screenings — e.g. `GET /v1/cinemas`, `GET /v1/cinemas/{id}/screenings`, `GET /v1/movies/{id}`, `GET /v1/screenings`. See the [API docs](api.md) for the full list.

A production instance is live at `https://marquise-api.fly.dev` — see [https://marquise-api.fly.dev/docs](https://marquise-api.fly.dev/docs) for the hosted OpenAPI UI.

See the [API docs](api.md) for details, including how to configure CORS origins, cache TTL, and rate limiting.

## Supported Sources

| Source | Type | Enrichment |
|--------|------|------------|
| Cineplex | API + web | Yes |
| CinemaCinema | SvelteKit API | Yes |
| Cinema Public | HTML scraping | Yes |
| Cinémathèque québécoise | HTML scraping | Yes |
| Cinéma Moderne | HTML scraping | Yes |
| Théâtre Outremont (Ciné-Outremont) | Firebase/Tuxedo ticketing API | Yes |

## Roadmap

- Admin CRUD API endpoints (write operations)
- Additional Montreal cinema sources
