# Changelog

## 0.10.0 (2026-07-09)

### New Features

- **New source: Cinémathèque québécoise**: Added a scraper source for Cinémathèque québécoise, fetching from the venue's OmniWeb ticketing portal (the cinema's own `cinematheque.qc.ca` site sits behind a Cloudflare challenge that blocks scraping, but its ticketing backend does not). Each day's schedule page embeds the full day's programming as an inline JS data blob (`gMovieData`) alongside a calendar of other available dates — `fetch_showtimes` bootstraps from today's page to discover the schedule window, then fetches each additional in-range date concurrently. `fetch_movie_detail` re-fetches a showtime's date page to pull synopsis/runtime/rating/poster enrichment, since the site has no separate film detail page. Titles carry a trailing parenthetical version marker (e.g. `"Romería (VOSTF)"`) which is split off into the `language` field, leaving `movie_title` clean. Registered as `"cinematheque"` in the DI container's source registry. Closes #47.

## 0.9.1 (2026-07-08)

### New Features

- **In-memory response caching for the read-only API**: `GET /cinemas`, `GET /cinemas/{id}/showtimes`, and `GET /movies/{id}` now serve repeat requests from an in-memory cache instead of re-invoking their use case and hitting the database every time, via the [`fastapi-cache2`](https://pypi.org/project/fastapi-cache2/) library's `@cache()` decorator and `InMemoryBackend`. `create_app()` initializes `FastAPICache` with a 1-hour default TTL — long enough to absorb the bulk of traffic between requests, short enough that responses are never more than an hour behind the nightly `marquise import all` refresh. The TTL is configurable via the optional `MARQUISE_API_CACHE_TTL_SECONDS` env var. `GET /health` is intentionally left uncached since it's a liveness probe.

### Bug Fixes

- **`GET /cinemas/{id}/showtimes` default date range no longer freezes under caching**: the `from`/`to` defaults ("today" through "+7 days") are now resolved by a dependency *before* the cached endpoint runs, so the cache key reflects the actual resolved dates instead of the raw, always-`None` query params. Previously, every request that omitted both dates collided on one cache entry frozen at whichever moment first populated it, for up to the TTL.
- **Default date range is now UTC and timezone-aware**: the default `from` used to be naive local server time, which the database layer silently treats as UTC — on a non-UTC host this shifted the "today" window by the server's UTC offset.
- **Mixed aware/naive `from`/`to` no longer 500s**: comparing an inverted range with one aware and one naive datetime raised an uncaught `TypeError` instead of the intended `ValueError`/422.
- **`GET /cinemas` now reuses the existing `CinemaController.list()`** instead of calling the use case directly, matching the CLI's call path as originally intended.

## 0.9.0 (2026-06-27)

### New Features

- **Read-only public REST API (FastAPI)**: Added a thin FastAPI layer (`infrastructure/api/`) exposing read access ahead of admin CRUD (#20): `GET /cinemas` (optional `name` filter), `GET /cinemas/{id}/showtimes?from=&to=`, `GET /movies/{id}`, plus a `GET /health` probe. Handlers do no data access themselves — they delegate to application use cases resolved from the DI container. Two new read-only use cases back the new endpoints: `GetMovieUseCase` and `GetCinemaShowtimesUseCase` (both additive; `ListCinemasUseCase` is reused via its public, no-auth path). The app is built by a `create_app()` factory whose lifespan opens/closes the database pool; tests inject a mocked container so they touch no database. All endpoints are public; admin mutations remain CLI-only. Added `fastapi` as a runtime dependency and `httpx` as a dev dependency (TestClient). Closes #20.
## 0.8.2 (2026-07-08)

### Bug Fixes

- **Deduplicate movies by normalized title, not exact string match**: `MovieRepository.find_by_title` previously matched titles exactly, so the same film scraped with a different case (`"The Batman"` vs `"the batman"`) or stray whitespace (`"Beau Is Afraid "`) created a duplicate `Movie` row and eventually violated the `movies.title` unique constraint. `SupabaseMovieGateway.find_by_title` now matches case-insensitively (`WHERE LOWER(title) = LOWER($1)`), and `ImportScreeningsUseCase._resolve_or_create_movies` normalizes whitespace on scraped titles before using them as lookup/dict keys. Movies already saved keep their original title for display — no data migration needed. Closes #23.

## 0.8.1 (2026-07-08)

### Bug Fixes

- **Fix daily `Scheduled import` workflow failures**: the nightly `marquise import all` run had been failing every day since June 30 for two reasons. First, `CineplexAdapter` mapped cinema display names to Cineplex theatre IDs by exact string match, and the DB's cinema row was named `"Scotiabank Cinema Montreal"` while the mapping only had the French `"Cinéma Banque Scotia Montréal"`, so every run raised `ValueError: No Cineplex location ID mapping for cinema 'Scotiabank Cinema Montreal'`. Added the English name as an alias for the same theatre ID (`9406`). Second, Cineplex occasionally lists the same underlying session (identical `external_id`/Vista session ID) under two different movie titles; the existing `(movie_title, showtime)` dedup key didn't catch this, so the second row hit the DB's unique constraint on `external_id` with `UniqueViolationError: duplicate key value violates unique constraint "screenings_external_id_key"`. `CineplexAdapter.fetch_showtimes` now dedupes on `external_id` first whenever it looks like a real session ID, falling back to the `(movie_title, showtime)` key otherwise.

## 0.8.0 (2026-06-27)

### New Features

- **Scheduled / bulk import path**: Added `marquise import all --days N` (default 7), which imports showtimes for every cinema that has a source assignment over a rolling window starting today. Cinemas without an assigned source are skipped (not errors) and per-cinema failures are collected without aborting the run, so unattended execution is resilient. The orchestration lives in a new `infrastructure/cli/import_commands.py` and reuses the existing `ImportScreeningsUseCase` via the controllers — no business logic in the CLI. A new `.github/workflows/scheduled-import.yml` runs it nightly (07:00 UTC) and on manual dispatch, authenticating via `MARQUISE_EMAIL`/`MARQUISE_PASSWORD` secrets alongside the existing `DATABASE_URL`/`SUPABASE_*` secrets. Per-cinema progress and results are now logged (`Importing <cinema>...`, then `[ok]`/`[skipped]`/`[failed]` lines with the date window up front), and per-cinema failures are caught and reported with their exception type and message instead of aborting the run with a bare, hard-to-debug error. Closes #22.

### Bug Fixes

- **Deduplicate Cineplex showtimes before upsert**: Cineplex lists the same showtime under multiple experiences (e.g. standard + IMAX), producing duplicate `(movie_title, showtime)` pairs. When these were upserted concurrently they raced on the DB unique constraint, causing `TypeError: 'NoneType' object is not iterable`. `CineplexAdapter.fetch_showtimes` now keeps the first occurrence of each `(movie_title, showtime)` pair before returning rows to the use case.

- **Restore Cineplex imports after the API began requiring a subscription key**: The Cineplex theatrical API now rejects keyless requests with `HTTP 401: Access denied due to missing subscription key`, which broke `marquise import all` for every Cineplex theatre. `CineplexSource` now sends the same anonymous `Ocp-Apim-Subscription-Key` that cineplex.com ships in its own frontend. Because Cineplex rotates that key, it is discovered at request time via the new `_discover_subscription_key` helper — it downloads the homepage, walks the referenced Next.js JS chunks, and extracts the key sent alongside the theatrical API — so imports keep working across rotations. An explicitly configured `CINEPLEX_API_KEY` still takes precedence; a baked-in key and the last successfully discovered key serve as fallbacks if discovery fails.
## 0.7.11 (2026-06-27)

### Technical Debt

- **Smaller cleanups batch**: A set of isolated, low-risk cleanups (#24): added shared `sample_cinema`/`sample_movie`/`sample_screening` fixtures to `tests/conftest.py`; hoisted the repeated per-command `import asyncio` to a single top-level import in the CLI command modules; deleted the dead `_select_cinema_public` helper; moved `GatewayError` to a new `protocols/base.py` (re-exported from `protocols.cinema` for back-compat); made `Movie.is_recent` use `datetime.now(UTC)`; converted the remaining NumPy-style gateway class docstrings to Google style; and dropped the dead ISO-string branch from the screening repository's `_parse_datetime` (the gateway always returns `datetime`). The `CinemaController.list`/`list_cinemas` naming consolidation was deferred as it is entangled with the auth-layer refactors (#11/#12). Closes #24.

## 0.7.10 (2026-06-27)

### Technical Debt

- **Replace gateway `dict` + `__inserted` with a typed `SaveOutcome`**: `ScreeningGateway.save` now returns a frozen `SaveOutcome(row, inserted)` dataclass instead of a plain `dict` carrying a magic `__inserted` key that callers had to `.pop()`. The Supabase gateway strips the internal SQL column and wraps the result; `SupabaseScreeningRepository.save` consumes `outcome.row`/`outcome.inserted`. No behaviour change — the repository still returns `(Screening, bool)`. Closes #18.

## 0.7.9 (2026-06-27)

### Bug Fixes

- **Validate `ShowtimeRow` at the scraper boundary**: `ShowtimeRow` gained a `__post_init__` that rejects empty/whitespace movie titles and naive (timezone-unaware) showtimes, so malformed scraped rows can no longer propagate toward the database. The source registry now also skips rows with blank titles defensively. Closes #19.

## 0.7.8 (2026-06-27)

### Chore

- Remove the old OpenCode plan that was accidentally published.

## 0.7.7 (2026-06-27)

### Infrastructure

- **Add `ty` type checker (non-blocking CI rollout)**: Introduced [`ty`](https://github.com/astral-sh/ty) (Astral's type checker) as a dev dependency alongside the existing uv + Ruff toolchain. Added a `[tool.ty.environment]` config (Python 3.13, `src` root) and a `Type check (ty)` step to the CI `quality` job marked `continue-on-error: true`, so it reports diagnostics without failing the build while the initial backlog (5 diagnostics at time of writing) is triaged. Documented `uv run ty check src` in `CONTRIBUTING.md` and `AGENTS.md`. Fixing the surfaced diagnostics and flipping CI to blocking are tracked as follow-ups. Closes #34.

## 0.7.6 (2026-06-27)

### Architecture

- **Stop mutating `Movie` in place during enrichment**: `_apply_enrichment` in `import_screenings.py` previously mutated a `Movie` entity in place, contradicting the project's value-object intent and making concurrent imports and future event sourcing fragile. It is now a pure function that returns a new `Movie` via `dataclasses.replace()`, populating only the fields that are currently null. Both call sites capture the returned instance, and `movies_to_save` is rebuilt after enrichment so the enriched (not the pre-enrichment) instances are persisted. As part of the change, the 11-field enrichment list — which was duplicated between `_apply_enrichment` and `_needs_enrichment` — was extracted into a shared `_ENRICHABLE_FIELDS` constant to prevent drift. No observable behaviour change; all existing tests pass. Closes #14.

### Technical Debt

- **Standardize on `str | None` over `Optional[str]`**: All `Optional[X]` type annotations across `src/`, `bin/`, and `tests/` were rewritten to the idiomatic `X | None` form, and the now-unused `from typing import Optional` imports were dropped. The Ruff `UP` (pyupgrade) rule set was added to `[tool.ruff.lint]` to enforce this going forward. Incidental modernizations surfaced by the rule were also applied: deprecated `typing.Tuple` imports removed and `run_spinner` converted to PEP 695 type parameters. Annotation-only change with no runtime behaviour difference; all 402 unit tests pass. Closes #16.

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
