# Showtime Sources

## Overview

Marquise aggregates showtimes from many different cinemas. Each cinema gets
its showtime data from a different source — some scrape their website, some
call an API, some parse a PDF schedule.

A **Source** is the abstraction for "a way to get showtimes from a particular
cinema chain or independent cinema." Sources are **not baked into the code**
for each cinema. Instead, the mapping is dynamic:

```
Cinema ──assigned to──> Source (e.g. "cineplex") ──fetches via──> CineplexSource
                        ^ stored in DB:                        ^ registered in
                          cinema_source_assignments               DI container
```

This means:
- Adding a new cinema that already has a source is just assigning it in the DB
- Adding a new source is a code change (new class + 1 line in the container)
- The `Cinema` entity has zero knowledge of sources

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│  Scraping pipeline (CLI/Cron, one-time)                    │
│                                                           │
│  FetchShowtimesUseCase                                    │
│    → GetCinemaSourceUseCase     (which source?)            │
│    → SourceRegistry.get(name)   (resolve to implementation)│
│    → Source.fetch_showtimes()         (returns raw dicts)        │
│    → map dicts → Movie/Screening entities                  │
│    → save via MovieRepository, ScreeningRepository         │
│                                                           │
│  Showtime results are stored in the DB permanently.        │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│  API (FastAPI, always-on)                                  │
│                                                           │
│  Reads showtimes from DB via repository queries.           │
│  Never calls external sources directly.                    │
└───────────────────────────────────────────────────────────┘
```

## Domain Model

| Entity / VO | Where | Purpose |
|---|---|---|
| `SourceDefinition` | Domain | A source's identity: name, display name, description |
| `SourceName` | Domain | Value object wrapping a string (e.g. `"cineplex"`) |
| `CinemaSourceAssignment` | Domain | Links `CinemaId` → `SourceName` |

## Layer by layer

### Domain (`src/marquise/domain/`)
- `value_objects/source_name.py` — wraps `str`
- `entities/source_definition.py` — the source catalog entry
- `entities/cinema_source_assignment.py` — maps cinema → source

### Application (`src/marquise/application/`)
- `repositories/source_definition_repository.py` — ABC for source CRUD
- `repositories/cinema_source_assignment_repository.py` — ABC for assignments
- `use_cases/create_source.py` — register a new source
- `use_cases/list_sources.py` — list all sources
- `use_cases/delete_source.py` — remove a source
- `use_cases/assign_source.py` — link a cinema to a source
- `use_cases/unassign_source.py` — unlink a cinema
- `use_cases/get_cinema_source.py` — query assignment + source display name

### Interface Adapters (`src/marquise/interface_adapters/`)
- `repositories/protocols/showtime_source.py` — `ShowtimeSource(Protocol)` for gateways
- `repositories/protocols/source_definition.py` — gateway protocol for source DB table
- `repositories/protocols/cinema_source_assignment.py` — gateway protocol for assignment DB table
- `repositories/source_registry.py` — maps source name → `ShowtimeSource` instance
- `repositories/supabase/source_definition_repository.py` — adapts gateway → entities
- `repositories/supabase/cinema_source_assignment_repository.py` — adapts gateway → entities

### Infrastructure (`src/marquise/infrastructure/`)
- `supabase/gateways/source_definition.py` — SQL CRUD for `source_definitions`
- `supabase/gateways/cinema_source_assignment.py` — SQL CRUD for `cinema_source_assignments`
- `controllers/source_controller.py` — validates admin, calls use cases
- `cli/source_commands.py` — CLI commands for admin
- `sources/cineplex/gateways/source.py` — example stub source
- `sources/cinema_du_parc/gateways/source.py` — example stub source

## Database Setup

Run these SQL statements on your Supabase PostgreSQL instance:

```sql
-- Schema (if not already created)
CREATE SCHEMA IF NOT EXISTS marquise;

-- Source definitions catalog
CREATE TABLE IF NOT EXISTS marquise.source_definitions (
    name                TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    description         TEXT
);

-- Cinema-to-source assignments
CREATE TABLE IF NOT EXISTS marquise.cinema_source_assignments (
    cinema_id   TEXT PRIMARY KEY,
    source_name TEXT NOT NULL
);
```

## CLI Usage

### Managing sources

```bash
# Register a new source
marquise source create \
  --name cineplex \
  --display-name "Cineplex" \
  --description "Cineplex Canada showtimes"

# List all registered sources
marquise source list

# Delete a source (interactive)
marquise source delete
```

### Assigning sources to cinemas

```bash
# Link a cinema to a source
marquise source assign \
  --cinema-id <cinema-uuid> \
  --source-name cineplex

# Remove the link
marquise source unassign \
  --cinema-id <cinema-uuid>

# Show what source a cinema is using
marquise source show \
  --cinema-id <cinema-uuid>
```

### Workflow example

```bash
# 1. Create the source
marquise source create --name cineplex --display-name "Cineplex"

# 2. Create a cinema
marquise cinema create --name "Cineplex Ste-Foy" ...
# → outputs ID: 550e8400-e29b-41d4-a716-446655440000

# 3. Assign the source to the cinema
marquise source assign \
  --cinema-id 550e8400-e29b-41d4-a716-446655440000 \
  --source-name cineplex

# 4. Verify
marquise source show \
  --cinema-id 550e8400-e29b-41d4-a716-446655440000
```

## Adding a New Source

See the existing stubs for reference:

| File | Source | Requirement |
|---|---|---|---|
| `infrastructure/sources/cineplex/gateways/source.py` | `CineplexSource` | Flat params (to be implemented) |
| `infrastructure/sources/cinema_du_parc/gateways/source.py` | `CinemaDuParcSource` | Flat params (to be implemented) |

### Step-by-step

1. **Create the implementation file**

   ```
   src/marquise/infrastructure/sources/guzzo/gateways/source.py
   ```

   ```python
   """Guzzo cinemas showtime source."""

   from __future__ import annotations


   class GuzzoSource:  # structurally satisfies ShowtimeSource protocol
       """Showtime source for Guzzo Cinemas."""

       async def fetch_showtimes(self, venue_id: str) -> list[dict]:
           # Your scraping/API logic here
           # Accepts flat parameters — no domain entities
           return [
               {
                   "movie_title": "Inception",
                   "showtime": datetime(2026, 6, 7, 19, 30),
                   "price": 14.99,
                   "available_seats": 120,
               },
           ]
   ```

3. **Register it in the DI container**

   In `src/marquise/infrastructure/di/container.py`:

   ```python
   from marquise.infrastructure.sources.guzzo.gateways.source import GuzzoSource

   # Inside _source_registry property:
   registry.register("guzzo", GuzzoSource())
   ```

3. **Register it in the database**

   ```bash
   marquise source create --name guzzo --display-name "Guzzo Cinemas"
   ```

4. **Assign to a cinema**

   ```bash
   marquise source assign --cinema-id <cinema-uuid> --source-name guzzo
   ```

### Conventions

- Use the same name string in the container `.register("xxx", ...)` as in `marquise source create --name xxx`
- Infrastructure gateways accept **flat parameters only** (no domain entities)
- The gateway implementation is registered directly in ``SourceRegistry``
- Return plain ``dict`` objects — never domain entities