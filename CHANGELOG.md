# Changelog

## 0.7.6 (2026-06-27)

### Architecture

- **Stop mutating `Movie` in place during enrichment**: `_apply_enrichment` in `import_screenings.py` previously mutated a `Movie` entity in place, contradicting the project's value-object intent and making concurrent imports and future event sourcing fragile. It is now a pure function that returns a new `Movie` via `dataclasses.replace()`, populating only the fields that are currently null. Both call sites capture the returned instance, and `movies_to_save` is rebuilt after enrichment so the enriched (not the pre-enrichment) instances are persisted. As part of the change, the 11-field enrichment list — which was duplicated between `_apply_enrichment` and `_needs_enrichment` — was extracted into a shared `_ENRICHABLE_FIELDS` constant to prevent drift. No observable behaviour change; all existing tests pass. Closes #14.

## 0.7.5 (2026-06-26)

### Bug Fixes

- **Fix misleading `updated_count` documentation and CLI labels**: The `OutputData` docstring described `updated_count` as "existing screenings skipped", but every non-inserted screening has `update()` called on it — nothing is ever skipped. Corrected the `OutputData.updated_count` docstring to "existing screenings found and updated in place" and the `ImportedScreeningData.imported` docstring to clarify the `False` case. Also fixed two CLI display strings in `source import`: per-row status `"already exists"` → `"updated"` and summary label `"already existed"` → `"updated"`. No logic changes; all existing test assertions remain valid. Closes #15.

## 0.7.4 (2026-06-26)

### Documentation

- **Rewrote `AGENTS.md`**: Trimmed from 1,434 lines to ~390 lines. Removed outdated sections referencing MongoDB and FastAPI (neither is in the current codebase). Updated tech stack (Supabase/asyncpg, Typer CLI), coverage gate (70% CI minimum, 80%+ target, 100% aspirational for core layers), and commands to match actual `marquise` CLI. Kept all enforced rules: type hints, Ruff, docstrings, layer boundaries, testing conventions, process guidelines. Closes #6.
- **Created `ARCHITECTURE.md`**: New ~120-line document describing the actual system — tech stack table, four-layer diagram with real directory paths, repository/gateway/source-adapter patterns, data flow, and planned FastAPI endpoints.
- **Updated `CONTRIBUTING.md`**: Replaced placeholder redirect to AGENTS.md with self-contained setup, day-to-day commands, CI pipeline description, branch naming, commit format, and PR checklist. Points to ARCHITECTURE.md and AGENTS.md for deeper context.

## 0.7.3 (2026-06-26)

### Technical Debt

- **Removed vestigial domain code**: Deleted `domain/exceptions/` package (6 files — `base`, `cinema`, `movie`, `screening`, `source`) and the unused `Price` and `ReleaseDate` value objects from `domain/value_objects/`. These artifacts were never imported in production code and accumulated from early development iterations. Their corresponding unit-test files (7 files) were also deleted. Closes #9.

## 0.7.2 (2026-06-26)

### Security

- **Fix SSL verification in scrapers**: Removed `ssl._create_unverified_context()` from all three scraper sources (`cinemacinema`, `cinemapublic`, `cineplex`). All outbound HTTP requests now use Python's default verified SSL context, which validates the certificate chain and hostname against the system CA bundle. Previously, scrapers silently accepted any certificate, making them vulnerable to MITM attacks that could corrupt the showtimes database.

Closes #8.

## 0.7.1 (2026-06-26)

### Infrastructure

- **CI Pipeline**: Added `.github/workflows/ci.yml` — runs on every push and pull request to `main`. The `quality` job installs dependencies via `uv`, checks formatting (`ruff format --check`), lints (`ruff check`), and runs the unit test suite with 80% coverage enforcement (`pytest --cov --cov-fail-under=80`). A separate `integration` job (manual trigger only) runs integration tests using `SUPABASE_URL`/`SUPABASE_KEY`/`DATABASE_URL` secrets.
- **Coverage gate**: Added `[tool.coverage.report]` with `fail_under = 80` to `pyproject.toml` — the quality gate is now enforced in CI, not just on paper.

Closes #7.

## 0.7.0 (2026-06-22)

### Highlights

- **Cineplex Source**: New scraper fetches showtimes from `apis.cineplex.com` and movie detail from `www.cineplex.com` (8 Montreal-area theatres: Banque Scotia, Quartier Latin, Forum, Carrefour Angrignon, Laval, Saint-Bruno, Brossard, Kirkland)
- **Movie Enrichment Pipeline**: `ImportScreeningsUseCase` now enriches new & partially-populated movies in parallel — fetches description, directors, cast, duration, genres, poster, trailer, rating, original title from Cineplex, Cinemacinema, and Cinema Public
- **Screening Metadata**: `Screening` gains `external_id`, `ticket_url`, `room`, `language` fields — gateways support backfilling via new `update()` method
- **Movie Schema Revamp**: `release_date` → `release_year`; 6 new enrichment columns on `movies` table

### New Features

- **Source — Cineplex**: Full scraper at `infrastructure/sources/cineplex/` — authenticated API client for showtimes, Next.js page scraping for movie detail, mapping for 8 Montreal venues
- **Source Adapter — Cineplex**: `CineplexAdapter` in `interface_adapters/repositories/source_adapters/cineplex.py` — maps cinema names to Cineplex location IDs
- **Movie Enrichment**: `MovieEnrichmentData` dataclass, `fetch_movie_detail()` on `SourceRegistryQuery` / `ShowtimeSource` / `SourceAdapter` protocols; all three sources implement enrichment
- **Screening Metadata**: `ScreeningGateway.update()` protocol method + Supabase implementation — backfills optional fields on existing rows preserving current values via `COALESCE`
- **Import Pipeline**: `ImportScreeningsUseCase` collects source identifiers, fetches enrichment in parallel, skips already-enriched movies via `_needs_enrichment()` check
- **Configuration**: `CINEPLEX_API_KEY` env var added to settings

### Domain Changes

- **Movie**: `release_date: Optional[date]` replaced by `release_year: Optional[int]` (validates positive); 6 new optional enrichment fields (`poster_url`, `trailer_url`, `genres`, `original_title`, `rating`, `origin_countries`); `is_recent()` uses year arithmetic
- **Screening**: 4 new optional fields (`external_id`, `ticket_url`, `room`, `language`)

### Infrastructure

- **Migration 002**: `scripts/002_add_movie_screening_fields.sql` — adds enrichment columns to `movies` and metadata columns to `screenings`
- **Migration 001 updated**: `release_date` → `release_year` in SQL and Python migrator
- **Supabase Gateways**: `MovieGateway.save()` and `ScreeningGateway.save()` accept all new fields; `ScreeningGateway` gains `update()` with `COALESCE`-based merge
- **Repository Implementations**: Map all new fields; `_parse_date()` removed from `SupabaseScreeningRepository`
- **DI Container**: Registers Cineplex source + adapter; reads `CINEPLEX_API_KEY`

### Bug Fixes

- **Enrichment alignment**: `_resolve_or_create_movies` rewritten to use parallel `(title, identifier)` tuples, fixing a bug where enrichment data could be applied to the wrong movie

### Documentation

- `docs/sources.md` — rewritten with improved pipeline diagram, source comparison table (enrichment support), database schema docs, Cineplex section, configuration env vars table, updated "Adding a New Source" guide
- `docs/todo.md` — notes `__inserted` flag as leaky abstraction in `ScreeningGateway`

### Testing

- **Application**: 7 new `ImportScreeningsUseCase` tests — enrichment flows (new, existing, skip, mixed identifiers), screening update backfill, negative count validation
- **Domain**: Updated `Movie` tests for `release_year`, all enrichment fields, `is_recent` boundary cases
- **Interface Adapters**: New `test_cineplex_adapter.py` (4 tests); updated movie/screening repository tests for new fields
- **Integration**: All gateway tests updated for `release_year` schema change

## 0.6.0 (2026-06-10)

### Breaking

- **Screening entity refactor**: `movie_id`/`cinema_id` replaced with full `Movie`/`Cinema` object references; `price`, `available_seats`, `is_sold_out`, and `update_availability()` removed
- **CinemaSourceAssignment entity refactor**: `cinema_id`/`source_name` replaced with full `Cinema`/`SourceDefinition` object references; `__post_init__` validation removed
- **Price removal**: `Price` value object and `price` column stripped from all gateways, repositories, source scrapers, CLI output, and tests

### Refactors

- **Use cases simplified**: `GetCinemaSourceUseCase` and `ImportScreeningsUseCase` no longer depend on `SourceDefinitionRepository` — the assignment entity carries the full source definition
- **Migration consolidation**: Old `migrate_001_drop_not_null_release_date.py` replaced by a single `migrate_001_initial_schema.py` creating the full schema with FK constraints
- **Joined queries**: All gateway `find_by_*` methods now use SQL `JOIN`s with prefixed column aliases (`movie__id`, `cinema__name`, etc.), eliminating N+1 lookups
- **Schema-aware gateways**: All Supabase gateways respect a configurable `schema` setting

### Infrastructure

- **FK constraints**: `cinema_source_assignments` and `screenings` tables now have `REFERENCES ... ON DELETE CASCADE` foreign keys
- **Shared utilities**: New `_utils.py` with `extract_prefixed()` and `dict_to_cinema()` helpers for joined query result parsing

### Testing

- All tests updated to reflect entity refactors (full objects vs IDs, no price/availability)
- New tests: timezone-aware datetime parsing, ISO string showtime parsing, joined data entity construction
- Integration tests: proper FK parent seeding for gateway tests

## 0.5.0 (2026-06-07)

### Highlights

- **Screening Import Pipeline**: End-to-end `ImportScreeningsUseCase` — resolves a cinema's assigned source, fetches showtimes, auto-creates unknown movies, upserts screenings
- **Movie & Screening Repositories**: Full repository/gateway stacks — `MovieRepository`, `ScreeningRepository` interfaces, `MovieGateway`/`ScreeningGateway` protocols, Supabase implementations with upsert-on-conflict logic
- **Source Adapter Architecture**: `SourceAdapter` protocol bridges `Cinema` entities to source-specific parameters — adapters for Cinemacinema (Beaubien, du Parc, du Musée) and CinemaPublic (Casa d'Italia, Livart)
- **CinemaPublic Source Rewrite**: Complete reimplementation — fetches JSON-LD structured data for initial weeks, parallel AJAX `load_more_weeks` for extended ranges, HTML fragment parsing for event details
- **Interactive CLI**: `marquise source import` with cinema selector, date range picker, and Rich table summary; `marquise source list-available`; improved `register`/`unregister` with interactive prompts
- **Richer Domain Model**: `Movie` now tracks `directors`, `cast`, `description`, `duration_minutes`; `Screening` decoupled from full `Movie`/`Cinema` to `MovieId`/`CinemaId` value objects, with `is_upcoming()`, `has_ended()`, and `update_availability()` methods

### New Features

- **Use Case**: `ImportScreeningsUseCase` — orchestrates cinema resolution → source discovery → showtime fetch → movie creation → screening upsert, returns detailed import summary
- **CLI — Source**: `marquise source import` (interactive cinema + date range selection with Rich table output), `marquise source list-available` (shows code-registered sources), improved `register`/`unregister` with interactive pickers
- **Repository Interfaces**: `MovieRepository` (`save`, `find_by_id`, `find_by_title`), `ScreeningRepository` (updated `save` returns `tuple[Screening, bool]` for insert/update detection)
- **Gateway Protocols**: `MovieGateway` and `ScreeningGateway` — typed protocols in `interface_adapters/repositories/protocols/`
- **Supabase Gateways**: `SupabaseMovieGateway` (upsert on `title` conflict with `COALESCE`), `SupabaseScreeningGateway` (upsert on `(cinema_id, movie_id, showtime)` conflict with CTE-based insert/update detection)
- **Supabase Repositories**: `SupabaseMovieRepository`, `SupabaseScreeningRepository` — adapt gateway dicts ↔ domain entities, handle `__inserted` flag
- **Source Adapters**: `SourceAdapter` protocol, `CinemaCinemaAdapter` (name → venue slug), `CinemaPublicAdapter` (name → venue slug)
- **Source Registry**: `SourceRegistry` now implements `SourceRegistryQuery` — resolves source definitions to adapters, maps raw dicts to `ShowtimeRow` dataclasses with timezone-aware datetime parsing
- **Source Registry Query**: New `RegistrySourceEntry` and `ShowtimeRow` dataclasses, `fetch_showtimes()` and `list_available()` abstract methods
- **Controller**: `list_registry_sources()` (public) and `import_screenings(cinema_id, start_date, end_date)` (admin) on `SourceController`
- **Application Exceptions**: `MovieNotFoundError`, `ScreeningAlreadyExistsError`, `ScreeningNotFoundError`
- **Settings**: Added `schema: str = "marquise"` for configurable database schema
- **Migration Script**: `scripts/migrate_001_drop_not_null_release_date.py` — drops NOT NULL on `movies.release_date`, `movies.directors`, `movies.cast_members`
- **Scrape Script**: `bin/scrape_cinemapublic.py` — standalone CLI for debugging Cinema Public showtimes per venue

### Domain Changes

- **Movie**: New optional fields `directors`, `cast`, `duration_minutes`, `description`; `release_date` now optional; new `is_recent(years=1)` method; validation for non-empty director tuples and positive duration
- **Screening**: `movie_id`/`cinema_id` types changed from full entities to `MovieId`/`CinemaId` value objects; `available_seats` and `is_sold_out` now `init=False`; new `is_upcoming()`, `has_ended()`, `update_availability(seats_sold)` methods

### Architecture

- **Full data flow**: CLI → `SourceController` → `ImportScreeningsUseCase` → `SourceRegistryQuery.fetch_showtimes()` → `SourceAdapter` → source scraper → `ShowtimeRow` → movie/screening upsert
- **Source adapters decouple cinema identity** from scraper implementation — adding a new cinema to an existing source is just an adapter mapping entry

### Documentation

- `docs/todo.md` — updated with new technical debt items for the import pipeline

### Testing

- **Application**: Full `ImportScreeningsUseCase` test suite with mocked repositories (success, no-movies, no-source, various empty/edge cases)
- **Domain**: Expanded `Movie` tests (director validation, optional fields, `is_recent` logic) and `Screening` tests (MovieId/CinemaId, availability, temporal methods)
- **Interface Adapters**: Unit tests for `SupabaseMovieRepository`, `SupabaseScreeningRepository` (mapping, error paths), `SourceRegistry` adapter registration and `fetch_showtimes` orchestration
- **Infrastructure**: Integration tests for `SupabaseMovieGateway` and `SupabaseScreeningGateway` (CRUD, upsert, date range filtering, conflict detection)
- **Controller**: Tests for `list_registry_sources` and `import_screenings` delegation
- All tests function-style, async with `pytest-asyncio`, per AGENTS.md conventions

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
