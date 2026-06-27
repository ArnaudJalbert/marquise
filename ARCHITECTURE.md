# Marquise Architecture

**Marquise** is a Montreal cinema showtimes aggregator. It fetches showtime data from multiple cinema sources (Cineplex, CinemaCinema, Cinema Public), normalises it, and stores it in a PostgreSQL database via Supabase.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| Package manager | uv |
| Database | Supabase (PostgreSQL via asyncpg) |
| CLI | Typer + Rich |
| Testing | pytest + pytest-asyncio |
| Linting / formatting | Ruff |
| Coverage gate | 70% CI minimum (target: 80%+; 100% for domain/application) |

## Four-Layer Structure

Marquise follows **Clean Architecture**. Dependencies point **inward only** — outer layers depend on inner layers, never the reverse.

```
┌─────────────────────────────────────────────────────────┐
│  src/marquise/infrastructure/                           │
│  CLI (Typer), DI container, auth, source scrapers,     │
│  Supabase gateways                                      │
├─────────────────────────────────────────────────────────┤
│  src/marquise/interface_adapters/                       │
│  Repository implementations (Supabase),                │
│  source adapters, gateway protocols                     │
├─────────────────────────────────────────────────────────┤
│  src/marquise/application/                              │
│  Use cases, repository interfaces, exceptions           │
├─────────────────────────────────────────────────────────┤
│  src/marquise/domain/                                   │
│  Entities (Cinema, Movie, Screening),                   │
│  value objects (CinemaId, MovieId, Showtime, …)         │
└─────────────────────────────────────────────────────────┘
```

### Key directories

```
src/marquise/
├── domain/
│   ├── entities/          # Cinema, Movie, Screening
│   └── value_objects/     # CinemaId, MovieId, ScreeningId, Showtime, SourceName
├── application/
│   ├── exceptions/        # ApplicationError hierarchy
│   ├── repositories/      # Abstract repository interfaces (ABCs)
│   └── use_cases/         # ImportScreeningsUseCase, CRUD use cases
├── interface_adapters/
│   └── repositories/
│       ├── protocols/     # Gateway protocols (typing.Protocol)
│       ├── supabase/      # Repository implementations (entity mapping)
│       └── source_adapters/  # Cineplex, CinemaCinema, CinemaPublic adapters
└── infrastructure/
    ├── cli/               # Typer app and command modules
    ├── controllers/       # CinemaController (thin CLI wiring layer)
    ├── di/                # Dependency injection container
    ├── auth/              # Admin authentication
    ├── supabase/
    │   ├── config/        # Connection configuration
    │   └── gateways/      # Raw SQL operations (cinema, movie, screening, …)
    └── sources/
        ├── cineplex/      # Cineplex scraper (API + web)
        ├── cinemacinema/  # CinemaCinema scraper
        └── cinemapublic/  # Cinema Public scraper
```

## Key Patterns

### Repository pattern

Abstract interfaces live in `application/repositories/` as ABCs. Concrete Supabase implementations live in `interface_adapters/repositories/supabase/` and translate between gateway dicts and domain entities.

### Gateway pattern

Raw SQL (asyncpg) is isolated in `infrastructure/supabase/gateways/`. Gateways implement the `typing.Protocol` types defined in `interface_adapters/repositories/protocols/`. Repositories in `interface_adapters/repositories/supabase/` call the gateway and convert the results to domain entities — no SQL leaks above this layer.

### Source adapter pattern

Each cinema source has a scraper under `infrastructure/sources/<source>/` and an adapter under `interface_adapters/repositories/source_adapters/`. Adapters translate raw `ShowtimeRow` dicts from scrapers into the format expected by use cases. The `source_registry.py` maps source names to adapter classes at runtime.

## Data Flow

```
marquise source import
  → CLI command (infrastructure/cli/source_commands.py)
  → CinemaController (infrastructure/controllers/)
  → ImportScreeningsUseCase (application/use_cases/)
    → SourceAdapter.fetch_showtimes()      # external HTTP
    → MovieRepository.find_by_title()      # Supabase
    → MovieRepository.save()
    → ScreeningRepository.save()           # upsert
  → OutputData displayed via Rich
```

## Planned Additions

- **FastAPI REST API** — read-only public endpoints planned:
  - `GET /cinemas`
  - `GET /cinemas/{id}/showtimes?from=&to=`
  - `GET /movies/{id}`

## Further Reading

- Source architecture: [`docs/sources.md`](docs/sources.md)
- Known technical debt: [`docs/todo.md`](docs/todo.md)
- Development rules: [`AGENTS.md`](AGENTS.md)
- Setup and commands: [`CONTRIBUTING.md`](CONTRIBUTING.md)
