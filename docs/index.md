# Marquise

Montreal cinema showtimes — aggregated, normalized, and queryable.

Marquise scrapes showtime data from multiple theater chains and independent cinemas across Montreal, normalizes it into a unified schema, and stores it in a PostgreSQL database. It ships as a CLI for data management and will expose a REST API for querying.

## What's in here

| Section | What you'll find |
|---|---|
| [Architecture](architecture.md) | Layer diagram, key patterns, data flow |
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

## Supported Sources

| Source | Type | Enrichment |
|---|---|---|
| Cineplex | API + web | Yes |
| CinemaCinema | SvelteKit API | Yes |
| Cinema Public | HTML scraping | Yes |

## Roadmap

- **FastAPI REST API** — read-only public endpoints (`GET /cinemas`, `GET /cinemas/{id}/showtimes`, `GET /movies/{id}`)
- Additional Montreal cinema sources
