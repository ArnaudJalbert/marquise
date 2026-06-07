# Changelog

## 0.4.0 (2026-06-07)

### Highlights

- **Showtime Source Domain**: `SourceDefinition` and `CinemaSourceAssignment` entities, `SourceName` value object — model the dynamic mapping between cinemas and their showtime data providers
- **Source Management CLI**: Full `marquise source` command tree — register, delete, list, assign, unassign, and query sources
- **Dynamic Source Resolution**: `ShowtimeSource` protocol + `SourceRegistry` — decouples cinemas from their data providers; adding a new source is just code + DB registration
- **Cinemacinema Source**: First concrete source implementation — scrapes `cinemacinema.ca` SvelteKit `__data.json` format (Cinémas Beaubien, du Parc, du Musée)
- **Gateway Protocols for Sources**: `SourceDefinitionGateway` and `CinemaSourceAssignmentGateway` protocols in `interface_adapters`, with Supabase implementations
- **100% Coverage**: Complete test suite for all new code across domain, application, and interface_adapters layers

### New Features

- **CLI — Source**: `marquise source register`, `marquise source delete`, `marquise source list-registered`, `marquise source assign`, `marquise source unassign`, `marquise source get-cinema-source`, `marquise source list-registry`
- **Use Cases**: `CreateSourceUseCase`, `DeleteSourceUseCase`, `ListSourcesUseCase`, `AssignSourceUseCase`, `UnassignSourceUseCase`, `GetCinemaSourceUseCase`, `ListRegistrySourcesUseCase` — each with validated `InputData`/`OutputData` inner classes
- **Gateway Protocols**: `SourceDefinitionGateway` (save, find_by_name, find_all, delete) and `CinemaSourceAssignmentGateway` (save, find_by_cinema, delete_by_cinema, find_all) — typed protocols in `interface_adapters/repositories/protocols/`
- **Supabase Gateways**: `SupabaseSourceDefinitionGateway` and `SupabaseCinemaSourceAssignmentGateway` — SQL CRUD for `source_definition` and `cinema_source_assignment` tables
- **Source Implementation**: `CinemacinemaSource` — asynchronous HTTP fetch + SvelteKit devalue parser for `cinemacinema.ca/en/schedule/__data.json`
- **Source Registry**: `SourceRegistry` adapter (resolves `SourceName` → `ShowtimeSource` implementation) + `ListRegistrySourcesUseCase` to query available implementations
- **Controller**: `SourceController` — wraps all source use cases with `validate_admin()` guard
- **DI Container**: Full wiring for source services — gateways → repositories → use cases → controller
- **Application Exceptions**: `SourceAlreadyExistsError`, `SourceNotFoundError`, `CinemaSourceAssignmentNotFoundError`, `CinemaSourceAssignmentAlreadyExistsError`

### Documentation

- `docs/sources.md` — comprehensive architecture guide covering source model, data flow diagrams, domain model table, CLI usage, and how to add new sources

### Testing

- **Domain**: Unit tests for `SourceDefinition`, `CinemaSourceAssignment` entities and `SourceName` value object
- **Application**: Use case tests for all 7 source use cases with `create_autospec` mocks (create, delete, list, assign, unassign, get-cinema-source, list-registry)
- **Interface Adapters**: Gateway protocol tests, Supabase repository implementation tests (success + error paths), controller unit tests
- **Infrastructure**: Integration tests for Supabase source definition and assignment gateways against real tables
- **CLI**: Full command tests for all `marquise source` subcommands
- **Exceptions**: Unit tests for source-related domain and application exception hierarchies
- All tests function-style, async with `pytest-asyncio`, per AGENTS.md conventions

## 0.3.0 (2026-06-06)

### Highlights

- **CLI Application**: New Typer-based CLI with `marquise auth` and `marquise cinema` subcommands
- **Authentication Flow**: `SupabaseAuthService` with email/password login, token refresh, and session persistence to `~/.marquise/auth.json`
- **Full Cinema CRUD**: Create, list (with name filter), update, and delete cinemas via CLI
- **Dependency Injection Container**: Central `Container` class replaces old `dependencies.py` — manages lifecycle (initialize/shutdown), no more module-level singletons
- **`website` Field**: Added to `Cinema` entity, all DTOs, gateway SQL, and repository mappings
- **AGENTS.md §11.6**: New "No Module-Level Mutable State" rule enforces per-call DI
- **Exception Isolation**: Domain exceptions no longer leak past the application boundary — use cases raise `ApplicationError` subclasses only

### New Features

- **CLI — Auth**: `marquise auth login` (prompts for email/password), `marquise auth logout`, `marquise auth status`
- **CLI — Cinema**: `marquise cinema create` (prompts for name/address/city/website), `marquise cinema list` (with `--name` filter), `marquise cinema delete`, `marquise cinema update`
- **Use Cases**: `DeleteCinemaUseCase`, `ListCinemasUseCase`, `UpdateCinemaUseCase` — each with validated `InputData`/`OutputData` inner classes
- **Gateway Protocol**: `CinemaGateway` expanded with `update()`, `delete()`, `find_all()` methods; `save()` now accepts `website`
- **Gateway Implementation**: `SupabaseCinemaGateway` — SQL for `UPDATE`, `DELETE`, `SELECT ... ORDER BY name`, and `LIKE`-based name filter
- **Repository Interface**: `CinemaRepository` — `find_all()`, `update()`, `delete()` added
- **Repository Implementation**: `SupabaseCinemaRepository` — delegates to gateway, maps `GatewayError` → `CinemaNotFoundError` on update
- **Auth Protocol**: `AuthService` protocol + `AuthSession` dataclass in `interface_adapters/repositories/protocols/auth.py`
- **Auth Implementation**: `SupabaseAuthService` with admin role verification and automatic token refresh on expiry
- **Controllers**: `AuthController` wraps auth service; `CinemaController` wraps all cinema use cases with `validate_admin()` guard
- **Dependency Injection**: `Container` class in `infrastructure/di/container.py` wires settings → gateways → repositories → use cases → controllers
- **Settings**: Added `supabase_url` and `supabase_publishable_key` fields

### Breaking

- `infrastructure/supabase/dependencies.py` removed — use `Container` from `infrastructure/di/container.py` instead
- `CinemaAlreadyExistsError` and `CinemaNotFoundError` moved from `domain.exceptions` to `application.exceptions` — use cases and repository implementations now raise application-layer exceptions only
- `DeleteCinemaUseCase.execute` and `CreateCinemaUseCase.execute` now raise `ApplicationError` subclasses instead of `DomainError` subclasses

### Documentation

- **AGENTS.md §11.7**: New "Domain Exceptions Must Not Leak" rule with examples

### Testing

- **Use Cases**: Unit tests for `DeleteCinemaUseCase`, `ListCinemasUseCase`, `UpdateCinemaUseCase` with mocked repositories
- **Repository**: Unit tests for `find_all`, `update`, `delete` on `SupabaseCinemaRepository` (including `CinemaNotFoundError` path)
- **Gateway**: Integration tests for `update`, `delete`, `find_all` on `SupabaseCinemaGateway`
- **Website Field**: All existing tests updated to include `website` parameter
- **Input/Output Validation**: Tests for website empty/whitespace rejection in both `InputData` and `OutputData`

## 0.2.0 (2026-06-06)

### Highlights

- **Gateway Protocol Pattern**: `CinemaGateway` protocol decouples infrastructure SQL from entity mapping
- **Robust Error Handling**: `UniqueViolationError` → `GatewayError` → `CinemaIdAlreadyExistsError` with descriptive messages
- **Price Self-Validation**: `Price` value object now validates non-negative in `__post_init__`
- **Infrastructure Hardening**: `sanitize_dsn()` handles `@` in passwords, `load_dotenv()` moved from import-time to first-call
- **100% Core Coverage**: domain, application, and interface_adapters layers fully covered

### Breaking

- `SupabaseCinemaRepository` moved from `interface_adapters/repositories/` root into `supabase/` subdirectory
- Old `application/dtos/` directory removed — DTOs are now inner classes of use cases
- `exists_by_id` no longer called proactively in `CreateCinemaUseCase` (UUID collision handled by DB constraint)
- `save()` in `SupabaseCinemaGateway` is now a pure `INSERT` (was `UPSERT`) — raises `GatewayError` on PK collision

## 0.1.0 (2026-06-06)

### Domain Layer

- **Entities**: `Cinema`, `Movie`, `Screening` with full validation in `__post_init__`
- **Value Objects**: `CinemaId`, `MovieId`, `ScreeningId`, `Showtime`, `ReleaseDate`, `Price`, `DateValue`, `IdValue` — `Price` validates non-negative in `__post_init__`
- **Domain Exceptions**: `DomainException`, `MovieError`, `CinemaError`, `ScreeningError`, `MovieNotFoundError`, `CinemaNotFoundError`, `CinemaAlreadyExistsError`, `ScreeningNotFoundError`

### Application Layer

- **Use Case**: `CreateCinemaUseCase` with duplicate name+address detection — UUID collision handled via DB constraint + descriptive `CinemaIdAlreadyExistsError`
- **DTOs**: `CreateCinemaUseCase.InputData` / `OutputData` (frozen dataclasses with validation, inner classes of the use case)
- **Repository Interface**: `CinemaRepository` (abstract, async methods for `save` / `find_by_id` / `find_by_name_and_address` / `exists_by_id`)
- **Application Exceptions**: `ApplicationError`, `CinemaIdAlreadyExistsError`

### Interface Adapters Layer

- **Gateway Protocol**: `CinemaGateway` — `typing.Protocol` defining the data-access contract (returns plain dicts, no domain/ORM types)
- **Gateway Error**: `GatewayError` — wraps infrastructure-level failures (e.g. `UniqueViolationError`)
- **Repository Implementation**: `SupabaseCinemaRepository` — maps gateway dicts ↔ domain entities, catches `GatewayError` → `CinemaIdAlreadyExistsError`
- **Architecture**: Clean separation — gateway (SQL) in `infrastructure`, protocol + adapter in `interface_adapters`
- **Deleted**: Old flat `SupabaseCinemaRepository`, unused `application/dtos/` directory

### Infrastructure Layer

- **Database**: `Database` class managing asyncpg connection pool (connect/disconnect/pool property)
- **DSN Sanitization**: `sanitize_dsn()` — robust percent-encoding of special characters in passwords (handles `#`, `@`, `%` with right-to-left greedy regex)
- **Gateway**: `SupabaseCinemaGateway` — pure `INSERT` with `UniqueViolationError` → `GatewayError` wrapping
- **Settings**: `Settings` frozen dataclass for `DATABASE_URL` env var
- **Dependencies**: `get_settings()` — lazy `load_dotenv()` call at first invocation (no import-time side effects)

### Documentation

- `AGENTS.md` — comprehensive development guide covering Clean Architecture, layer responsibilities, coding standards, testing strategy, and process guidelines
- `mkdocs.yml` + `docs/` — MkDocs site with Material theme, nav structure, and `mkdocstrings` plugin
- `docs/todo.md` — tracked technical debt (Screening entity reference refactor)
- `docs/setup/supabase-cinema-table.md` — Supabase table setup guide

### Testing

- **Domain**: 100% coverage — all entities, value objects, and domain services tested
- **Application**: 100% coverage — `CreateCinemaUseCase` async tests with `create_autospec` mocks, DTO input/output validation, exception hierarchy
- **Interface Adapters**: 100% coverage — `SupabaseCinemaRepository` unit-tested with mocked `CinemaGateway` (including error-wrapping path)
- **Infrastructure**: `sanitize_dsn()` tested with `#`, `@`, `%` in passwords; `Database` lifecycle tests (connect/disconnect/pool) with monkeypatched asyncpg
- **Integration**: `SupabaseCinemaGateway` integration tests against real PostgreSQL table (requires `DATABASE_URL` env var)
- **Conventions**: All tests are function-style (no test classes, per AGENTS.md §9.6)