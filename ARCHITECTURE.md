# Marquise Architecture

Marquise is an open-source **Montreal cinema showtimes aggregator**. It collects showtime data from three sources (Cineplex, CinemaCinema, CinemaPublic), normalizes it, stores it in Supabase (PostgreSQL), and exposes it through a Typer CLI today — with a read-only FastAPI REST API planned.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| Package manager | uv |
| Database | Supabase (PostgreSQL via asyncpg) |
| CLI | Typer + Rich |
| Test runner | pytest + pytest-asyncio |
| Linter / formatter | Ruff |

## Layers

Marquise follows Clean Architecture. Dependencies point inward only — outer layers know about inner layers, never the reverse.

```
┌────────────────────────────────────────────────────────┐
│  src/marquise/infrastructure/                          │
│  CLI (Typer), DI container, Supabase gateways, config │
├────────────────────────────────────────────────────────┤
│  src/marquise/interface_adapters/                      │
│  Repository implementations, source adapters           │
├────────────────────────────────────────────────────────┤
│  src/marquise/application/                             │
│  Use cases, repository interfaces, application errors  │
├────────────────────────────────────────────────────────┤
│  src/marquise/domain/                                  │
│  Entities, value objects (no external dependencies)    │
└────────────────────────────────────────────────────────┘
```

### Domain layer (`src/marquise/domain/`)

Entities and value objects with no external dependencies. Key entities: `Cinema`, `Movie`, `Screening`, `SourceDefinition`, `CinemaSourceAssignment`.

### Application layer (`src/marquise/application/`)

- **Use cases**: `CreateCinemaUseCase`, `ImportScreeningsUseCase`, and ~10 others — each exposes `InputData` / `OutputData` inner dataclasses.
- **Repository interfaces**: ABCs in `application/repositories/` — `CinemaRepository`, `MovieRepository`, `ScreeningRepository`, etc.
- **Application exceptions**: `ApplicationError` subclasses raised at use-case boundaries.

### Interface adapters layer (`src/marquise/interface_adapters/`)

- **Repository implementations**: Supabase implementations in `repositories/supabase/` — adapt gateway dicts ↔ domain entities.
- **Gateway protocols**: `typing.Protocol` definitions in `repositories/protocols/` — describe what each gateway must provide; no SQL or infrastructure imports.
- **Source adapters**: `repositories/source_adapters/` — bridge `Cinema` entities to source-specific fetch parameters.

### Infrastructure layer (`src/marquise/infrastructure/`)

- **CLI**: Typer app in `cli/` — `marquise auth`, `marquise cinema`, `marquise source`.
- **Supabase gateways**: SQL in `supabase/gateways/` — implement gateway protocols, return plain dicts.
- **DI container**: `di/container.py` — wires settings → gateways → repositories → use cases → controllers.
- **Config**: `settings.py` reads env vars (`DATABASE_URL`, `SUPABASE_URL`, `CINEPLEX_API_KEY`, etc.).

## Key Patterns

### Repository pattern

ABCs in `application/repositories/` define the contract. Supabase implementations in `interface_adapters/repositories/supabase/` implement them. Use cases only depend on the ABC — swapping the database requires no domain or application changes.

### Gateway pattern

SQL and external HTTP live in `infrastructure/supabase/gateways/` and return plain dicts. `interface_adapters/repositories/protocols/` holds a `typing.Protocol` that describes each gateway's interface. The `interface_adapters` repository implementations take the protocol as a constructor argument and handle entity mapping only.

```
interface_adapters/repositories/protocols/cinema.py        ← CinemaGateway Protocol
interface_adapters/repositories/supabase/cinema_repository.py  ← maps dicts ↔ Cinema
infrastructure/supabase/gateways/cinema.py                  ← SQL lives here
```

### Source adapter pattern

Each showtime source (Cineplex, CinemaCinema, CinemaPublic) has:
- A scraper in `infrastructure/sources/<name>/`
- A `SourceAdapter` in `interface_adapters/repositories/source_adapters/` that maps cinema names to source-specific IDs
- Registration in `SourceRegistry`

Adding a new cinema to an existing source is just an adapter mapping entry — no scraper changes needed.

## Data Flow

### CLI command

```
marquise cinema list
  → CinemaController.list()
    → ListCinemasUseCase.execute(InputData)
      → CinemaRepository.find_all()        ← interface (application layer)
        → SupabaseCinemaRepository          ← implementation (interface_adapters)
          → SupabaseCinemaGateway           ← SQL (infrastructure)
            → Supabase / PostgreSQL
```

### Import pipeline

```
marquise source import
  → SourceController.import_screenings(cinema_id, start, end)
    → ImportScreeningsUseCase.execute(...)
      ├─ SourceRegistryQuery.fetch_showtimes()   → ShowtimeRow[]
      ├─ MovieRepository.find_by_title / save    → Movie entities
      ├─ parallel movie enrichment (description, cast, poster, …)
      └─ ScreeningRepository.save / update       → Screening entities
```

## Planned Additions

A read-only **FastAPI REST API** is the next major infrastructure addition:

```
GET /cinemas
GET /cinemas/{id}/showtimes?from=&to=
GET /movies/{id}
```

The use cases that power these endpoints already exist. Adding FastAPI is purely an infrastructure concern — no domain or application layer changes needed.

## Further Reading

- `docs/sources.md` — source architecture, scraper details, how to add a new source
- `docs/todo.md` — tracked technical debt
- `CONTRIBUTING.md` — setup, commands, CI, PR checklist
- `AGENTS.md` — coding rules and standards enforced in code review
