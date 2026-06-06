# Changelog

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