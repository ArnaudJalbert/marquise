# Changelog

Before 2026-07-15 this package was published as `marquise`.

## 2026-10-03

### v0.2.21

- Skip screening external-ID conflicts on insert and update without modifying existing rows. Log each skipped row and keep unrelated database failures fatal. Add PostgreSQL regression coverage. Closes #278.

## 2026-09-02

### v0.2.20

- **Keep credential-bearing dataclass representations safe**: passwords, bearer tokens, database URLs, and API keys are excluded from diagnostic `repr` output.

- **Harden authentication transport (2026-09-10)**: require HTTPS auth configuration, reject credential-bearing GoTrue redirects, and allow local HTTP only with an explicit literal-loopback development opt-in.

- **Add clean authentication core**: verify Supabase JWTs through a dedicated account identity reader and query, and expose configured Administrator authentication, invitation, and role-change use cases through `MarquiseFactory`. Roles live only in protected Supabase `app_metadata`. Invitations use Supabase's dedicated endpoint and retain HTTP status and safe provider detail for CLI diagnosis. Closes #263, #264, and #266.

## 2026-08-29

### v0.2.19

- **Centralize cinema screening imports**: use one injected application command for fetch, movie reconciliation, title mapping, and screening persistence in both CLI import paths.

### v0.2.18

- **Use readers for cinema and movie screening lists**: replace entity-backed listing use cases with configured queries backed by `ScreeningReader`. Closes #208.
- **Use configured read use cases directly**: expose cinema, movie, and screening read use cases through the public factory and remove obsolete controllers. Closes #188 and #189.
- **Split dependency wiring by responsibility**: isolate source registry, source management, and import use-case construction from the lifecycle container. Closes #190, #191, and #193.
- **Lighten screening search**: `SearchScreeningsUseCase` is replaced by `SearchScreeningsQuery` and a dedicated Supabase reader that projects only response columns into light `ScreeningSummary` values. Entity-based screening use cases keep using `ScreeningRepository`. Closes #205.

### v0.2.17

- **Bound source movie enrichment**: limit concurrent detail requests per cinema import to protect provider and event-loop capacity. Closes #229.

## 2026-08-28

### v0.2.16

- **Make screening pagination deterministic**: add a stable screening ID tie-breaker after showtime ordering.

### v0.2.15

- **Repair Cinéma Public booking URLs**: normalize malformed and relative booking paths emitted by the source adapter.

## 2026-08-26

### v0.2.13

- **Normalize movie title matching**: reuses titles that differ only by case, punctuation, or a leading article without matching contained titles; ambiguous or conflicting release-year matches create a new movie.

### v0.2.12

- **Add Cine Starz showtime source**: imports Cine Starz Côte-des-Neiges and Cine Starz Deluxe Cavendish schedules, stable ticket performance IDs, ticket URLs, and optional JSON-LD movie metadata. Closes #88.

### v0.2.11

- **Expose cinema listing use case**: `MarquiseFactory.list_cinemas_use_case` provides configured direct listing access for delivery apps. Closes #187.

## 2026-08-25

### v0.2.10

- **Remove `SourceController`**: source use cases are exposed through `MarquiseFactory` and public `marquise` API; controller wiring and export are removed. Closes #184.

## 2026-08-21

### v0.2.9

- **Expose cinema-source assignment query**: `MarquiseFactory.list_cinema_source_assignments_query` and top-level `ListCinemaSourceAssignmentsQuery` provide bulk assignment lookups without constructing domain entities.

### v0.2.8

- **Remove cinema update from `CinemaController`**: delivery consumers now use the public `UpdateCinemaUseCase` directly. Closes #167.

### v0.2.7

- **Expose update-cinema use case**: `MarquiseFactory.update_cinema_use_case` and top-level `UpdateCinemaUseCase` now provide CLI consumers with configured direct update access. Closes #166.

## 2026-08-18

### v0.2.6

- **Remove cinema deletion from `CinemaController`**: deletion is now exposed only through `DeleteCinemaUseCase`, allowing delivery code to invoke it directly. Closes #165.

### v0.2.5

- **Expose delete-cinema use case**: `MarquiseFactory.delete_cinema_use_case` and top-level `DeleteCinemaUseCase` now provide CLI consumers with configured direct deletion access. Closes #164.

### v0.2.4

- **Patch release**: no public API changes since v0.2.3.

### v0.2.3

- **Expose create-cinema use case**: `MarquiseFactory.create_cinema_use_case` and top-level `CreateCinemaUseCase` now provide CLI consumers with configured direct creation access. Closes #162.


## 2026-08-03

### v0.2.2

- **Remove CLI/controller authentication**: deletes the `AuthController`, `SupabaseAuthService`, and the `AuthService`/`AuthSession` protocols. `CinemaController` and `SourceController` no longer take an `auth_controller` or call `validate_admin()`. The `marquise.auth` property, `AuthController` and `MARQUISE_EMAIL`/`MARQUISE_PASSWORD` exports are removed from the public surface, and `supabase_url` / `supabase_publishable_key` are dropped from `Settings`. The `supabase` runtime dependency is removed. Authorization is left to the API, which may add admin checks in the future; for the CLI, possession of the SQL credentials is the security boundary.


## 2026-07-29

### v0.2.1

- **`CreateScreeningsCommand` updates on conflict instead of skipping**: when a `ScreeningAlreadyExistsError` is raised by `save()`, the command now calls `screening_repository.update()` to refresh the existing row. If the row disappears concurrently (`update` returns `None`), a new `ScreeningUpdateNotFoundError` is raised and the entry is counted as a skip.
- **Fix Cineplex ticket URL generation**: the gateway now prefers `session.ticketingRedesignUrl` and `session.ticketingUrl` from the API before falling back to the legacy deeplink construction. Removed the now-unused `film_url` parameter from `_build_ticket_url`.
- **Export `ScreeningUpdateNotFoundError`** from `marquise.application.exceptions`.


## 2026-07-20

### v0.2.0

- **Decompose `ImportScreeningsUseCase` into a controller-orchestrated workflow** (#13): the
  ~400-line use case that fetched showtimes, deduped/enriched movies, upserted screenings, and
  tallied counts is split into three focused, independently-tested use cases —
  `FetchShowtimesFromSourceQuery`, `EnsureMoviesExistCommand`, and `UpsertScreeningsCommand`.
  `SourceController.import_screenings` now sequences the three (a use case no longer orchestrates
  other use cases); all business rules, including the import counts and external_id
  skip-on-collision handling, stay inside the use cases. `import_screenings.py` is reduced to the
  shared response DTOs (`ImportedScreeningData`, `ImportScreeningsSummary`). The
  `SourceController.import_screenings` signature and returned fields are unchanged, so the CLI and
  API are unaffected.

### v0.1.3

- **Standardise test structure across the test suite**: extracted `import_screenings` DTO
  validation tests into a dedicated file (`test_import_screenings_input_output_data.py`),
  moved `test_showtime_row.py` into `application/repositories/` to mirror the source layout,
  removed unused shared fixtures from `tests/conftest.py`, renamed 5 source gateway test
  files from `test_source.py` to `test_{source}_gateway.py`, and replaced 17 instances of
  explicit `AsyncMock(...)` wiring in controller tests with the idiomatic
  `.return_value = ...` pattern. All changes are test-only; no production code was modified.


## 2026-07-17

### v0.1.2

- **`MovieRepository.find_by_ids` reused by `ListMoviesUseCase`**: new Clean Architecture plumbing backing the bulk-by-ids mode of `GET /v1/movies` — `SupabaseMovieGateway.find_by_ids` (`WHERE id = ANY($1)`, the codebase's first multi-value SQL lookup), `MovieGateway` protocol, `SupabaseMovieRepository`. `ListMoviesUseCase.InputData` gained an `ids` field; when set, `execute()` branches to `find_by_ids` instead of the title/pagination `find_all` path. `MovieController.list` gained a matching `ids` parameter.


## 2026-07-15

### v0.1.1

- **Fix inconsistent showtime timezone handling across scraper sources**: `cinemapublic`, `cinemamoderne`, `cinemacinema`, and `cinematheque` were emitting naive Montreal-local `showtime` strings with no UTC offset, while `outremont` and `cineplex` already emitted genuinely UTC-aware timestamps — the two conventions were silently incompatible with each other and with any client reading `showtime` as real UTC. Added `marquise.infrastructure.sources._timezone.montreal_local_to_utc_iso()`, a shared `zoneinfo`-based (`America/Toronto`, DST-correct) conversion helper, and switched the four naive sources to call it so every source now emits a real, unambiguous UTC ISO 8601 `showtime`.

### v0.26.0

- **Core public bootstrap API (#101, #102)**: adds a public bootstrap API for apps in `apps/` to depend on `marquise-core` without reaching into internal modules. New `MarquiseFactory` class in `packages/marquise-core/src/marquise/bootstrap.py` with lazy-loaded controller properties (`.cinema`, `.source`, `.auth`), `check_database_health()` method, and async context manager support. `create_factory()` async factory function and `create_factory_session()` async context manager for app integration. Public surface re-exported from `marquise/__init__.py` via `__all__`: `MarquiseFactory`, `create_factory`, `create_factory_session`, `CinemaController`, `SourceController`, `AuthController`. Import boundary enforcement: AST-based scanner (`tests/unit_tests/test_import_boundary.py`), `import-linter` contract in root `pyproject.toml`, and snapshot test (`tests/unit_tests/test_public_api.py`) prevents accidental `__all__` additions. Closes #101, #102.
- **Extract API and CLI into separate workspace packages**: removed delivery dependencies from `marquise-core`. Added `MovieController` and `ScreeningController`. Closes #105, #106.

### v0.25.0

- **Théâtre Outremont (Ciné-Outremont) showtime source**: adds a new `outremont` source with **exact showtimes**. Rather than the public `/cinema/` listing (which shows only a date), it reads the venue's Tuxedo Billet ticketing backend directly over plain HTTP — the same Firebase Realtime Database the site's SPA uses — by replaying its bootstrap: read the public `configuration.json` for the Firebase config, sign in anonymously via the Identity Toolkit REST API, resolve the venue channel, then read the `shows` node. Each show carries an `events` map of `eventId → epoch-millis`, yielding one screening per event at its exact UTC instant (so e.g. Le Gâteau du président surfaces both its 16:00 and 19:30 screenings, not just a date). Shows are filtered to the `Cinéma` report-category. `fetch_movie_detail` reads a single show document and parses its paragraph-delimited description into `original_title`, `directors`, `cast`, `release_year`, `origin_countries`, `genres`, `duration_minutes`, `rating`, `poster_url`, and synopsis. Follows the existing single-venue pattern: `OutremontSource` gateway (`infrastructure/sources/outremont/`), `OutremontAdapter` (`interface_adapters/repositories/source_adapters/outremont.py`), registered as `"outremont"` in the DI container's `SourceRegistry`. Stdlib-only (`urllib` + `json` + `certifi`); no new dependencies.

### v0.23.2

- **Drop redundant `OutputData` re-validation (#17)**: removes `__post_init__` checks on use-case `OutputData` fields that were already validated by the value they were copied from (a validated `CinemaId`/`SourceName`, or an entity/`InputData` field validated upstream) — e.g. `cinema_id`, `cinema_name`, `source_name`, `name`, `address`, `city`, `website` across `assign_source`, `create_cinema`, `create_source`, `delete_cinema`, `delete_source`, `get_cinema_source`, `import_screenings`, `list_cinemas`, `list_movies`, `list_registry_sources`, `list_sources`, `unassign_source`, and `update_cinema`. Keeps validation for genuinely computed/derived fields (e.g. `total`, `total_count`, `imported_count`, `updated_count`, `skipped_count`) where a bug in aggregation logic could otherwise produce an invalid value.

### v0.23.1

- **Fix all `ty` type errors and promote to blocking CI check**: resolves 8 diagnostics across 5 files — exception handler signature mismatches in `infrastructure/api/app.py` and `exception_handlers.py`, nullable `expires_at` in `infrastructure/auth/supabase_auth_service.py`, missing `urllib.error` import and untyped assignment in `infrastructure/sources/cinemacinema/gateways/source.py`, and list narrowing issue in `infrastructure/sources/cineplex/gateways/source.py`. Promotes `ty check` to a blocking CI step (was `continue-on-error: true`).


## 2026-07-13

### v0.23.0

- **`GET /cinemas/{cinema_id}` single-cinema endpoint (#63)**: adds a new read-only endpoint returning a single cinema by its ID (`id`, `name`, `address`, `city`, `website`), enabling the admin web app's cinema detail page to show the cinema's own metadata without pulling its showtimes. Backed by a new `GetCinemaUseCase` mirroring the existing `GetMovieUseCase` pattern — validated `InputData`/`OutputData`, uses `CinemaRepository.find_by_id`, raises `CinemaNotFoundError` (404) for unknown IDs. Cached and rate-limited per the existing read-endpoint conventions. Closes #63.

### v0.22.0

- **Screenings API endpoints epic (#128-#132)**: adds a reusable dynamic-filter `search()` method on `ScreeningRepository`/`ScreeningGateway` (`application/repositories/screening_repository.py`, `infrastructure/supabase/gateways/screening.py`), used by every new/changed endpoint below instead of duplicating WHERE-clause logic per route.
  - Every screening response now includes `cinema_id`/`cinema_name` alongside `movie_id`/`movie_title`.
  - `GET /v1/screenings`: general search across all cinemas, filterable by `movie`, `movie_id`, `cinema_id`, `from`/`to`, and `language`; paginated. New `SearchScreeningsUseCase`.
  - `GET /v1/screenings/{screening_id}`: fetch a single screening by ID. New `GetScreeningUseCase`.
  - `GET /v1/movies/{movie_id}/screenings`: list all of a movie's screenings. New `GetMovieScreeningsUseCase`.
  - `GET /v1/cinemas/{cinema_id}/movies`: list distinct movies currently screening at a cinema. New `GetCinemaMoviesUseCase`.
  - Extracted shared `resolve_showtimes_date_range` FastAPI dependency into `_dependencies.py`.
  - `GET /v1/screenings` is uncached; `GET /v1/screenings/{screening_id}` keeps cache.
  - `GET /v1/cinemas/{cinema_id}/showtimes` renamed to `GET /v1/cinemas/{cinema_id}/screenings` (breaking).


## 2026-07-12

### v0.21.2

- **Fix Cineplex Royalmount import failure**: adds missing `location_id` mapping for "Cinéma Cineplex Royalmount".
- **Fix Cinéma Cinéma import crash on unknown release year**: `_extract_release_year()` guards against `annee: 0`.
- **Live integration coverage for newly onboarded cinemas (#83-#86)**.

### v0.21.1

- **Post-deploy verification and docs for Fly.io production deployment**: smoke-tested live API; documents production URL; automated smoke-test step in CI. Closes #123.


## 2026-07-11

### v0.21.0

- **Docker image + Compose for the read-only API**: multi-stage Dockerfile, `.dockerignore`, `docker-compose.yml`, `.env.example`. Closes #119.

### v0.20.0

- **Structured JSON request logging**: `JsonFormatter` (stdlib `logging.Formatter`), `RequestLoggingMiddleware`, per-request `X-Request-ID` header, `ErrorResponse.request_id` field. Configurable via `MARQUISE_API_LOG_LEVEL`. Closes #55.

### v0.19.0

- **Polished OpenAPI docs**: expanded `FastAPI(description=...)`, `json_schema_extra` examples, field-level descriptions, `error_responses()` helper. Closes #57.

### v0.18.0

- **DB-aware readiness check (`GET /ready`)**: `Database.ping()`, `Container.check_database_health()`, `GET /ready` → 200/503. Closes #56.

### v0.17.0

- **Global exception handlers**: `exception_handlers.py` with `_APPLICATION_ERROR_MAPPING`, `ValueError` handler (422), catch-all `Exception` handler (500, never leaks message). `ErrorResponse` schema. Closes #51.

### v0.16.0

- **`GET /movies` list/search endpoint**: `title` filter, `ListMoviesUseCase`, `MovieRepository.find_all`. Closes #53.


## 2026-07-09

### v0.15.0

- **API versioning (`/v1` prefix)**: all routes except `/health` mounted under `/v1`. Closes #54.

### v0.14.0

- **Per-IP rate limiting**: slowapi, 60 req/min default, configurable via `MARQUISE_API_RATE_LIMIT`. Closes #50.

### v0.13.0

- **CORS support**: `CORSMiddleware` when `MARQUISE_API_CORS_ORIGINS` is set. Closes #52.

### v0.12.0

- **SQL-level pagination**: LIMIT/OFFSET + `COUNT(*) OVER()` in gateways; fastapi-pagination `Page`/`Params`.

### v0.11.0

- **New source: Cinéma Moderne**: scraper for Cinéma Moderne schedule pages. Closes #48.

### v0.10.1

- **Cineplex import no longer aborts on `external_id` collision**: per-row skip via `return_exceptions=True`.

### v0.10.0

- **New source: Cinémathèque québécoise**: OmniWeb ticketing portal scraper. Closes #47.

### v0.9.1

- **In-memory response caching**: fastapi-cache2 `@cache()` with 1h TTL, configurable.
- **Fix caching date range bug**: default `from`/`to` resolved before caching.
- **Default date range now UTC and timezone-aware**.
- **Mixed aware/naive `from`/`to` no longer 500s**.


## 2026-06-27

### v0.9.0

- **Read-only public REST API (FastAPI)**: endpoints for cinemas, showtimes, movies, plus health probe. New `GetMovieUseCase`, `GetCinemaShowtimesUseCase`. `create_app()` factory. Closes #20.

### v0.8.2

- **Deduplicate movies by normalized title**: case-insensitive `WHERE LOWER(title)` match; white-space normalization. Closes #23.

### v0.8.1

- **Fix daily scheduled import failures**: English name alias for Scotiabank; dedup on `external_id`.

### v0.8.0

- **Scheduled / bulk import path**: `marquise import all --days N`, cron workflow. `import_commands.py`. Closes #22.
- **Deduplicate Cineplex showtimes before upsert**.
- **Cineplex subscription key rotation**: `_discover_subscription_key` helper.

### v0.7.11

- **Smaller cleanups batch (#24)**: shared fixtures, async import hoisting, dead helper cleanup, `GatewayError` move, Google-style docstring conversion, datetime parsing cleanup.

### v0.7.10

- **Replace gateway `dict` + `__inserted` with typed `SaveOutcome`**. Closes #18.

### v0.7.9

- **Validate `ShowtimeRow` at the scraper boundary**: reject empty titles, naive datetimes. Closes #19.

### v0.7.8

- Remove the old OpenCode plan that was accidentally published.

### v0.7.7

- **Add `ty` type checker (non-blocking CI rollout)**. Closes #34.

### v0.7.6

- **Stop mutating `Movie` in place during enrichment**: pure function via `dataclasses.replace()`. Closes #14.
- **Standardize on `str | None` over `Optional[str]`**: Ruff `UP` rule. Closes #16.

### v0.7.5

- **Fix misleading `updated_count` documentation and CLI labels**. Closes #15.

### v0.7.4

- **Rewrote `AGENTS.md`** from 1,434 lines to ~390 lines. Closes #6.
- **Created `ARCHITECTURE.md`**: ~120-line document describing the actual system.
- **Updated `CONTRIBUTING.md`** with self-contained setup and CI pipeline.


## 2026-06-26

### v0.7.3

- **Removed vestigial domain code**: deleted domain exceptions package, unused value objects, and their test files. Closes #9.

### v0.7.2

- **Fix SSL verification in scrapers**: removed `ssl._create_unverified_context()`. Closes #8.

### v0.7.1

- **CI Pipeline**: `.github/workflows/ci.yml` — quality + integration jobs. Closes #7.
- **Coverage gate**: `fail_under = 80` in pyproject.toml.


## 2026-06-22

### v0.7.0

- **Cineplex Source**: scraper for 8 Montreal-area theatres.
- **Movie Enrichment Pipeline**: parallel enrichment from Cineplex, Cinemacinema, Cinema Public.
- **Screening Metadata**: `external_id`, `ticket_url`, `room`, `language` fields.
- **Movie Schema Revamp**: `release_date` → `release_year`; 6 new enrichment columns.
- **Domain changes**: `Movie` enrichment fields, `Screening` metadata, `Price` validation.
- **Infrastructure**: migration 002, gateway `update()`, DI container wiring.


## 2026-06-10

### v0.6.0

- **Screening entity refactor**: full `Movie`/`Cinema` object references; `price`, `available_seats`, `is_sold_out` removed.
- **CinemaSourceAssignment refactor**: full entity references instead of IDs.
- **Use cases simplified**: no longer depend on `SourceDefinitionRepository`.
- **Joined queries**: all gateway `find_by_*` use SQL JOINs with prefixed aliases, eliminating N+1 lookups.
- **FK constraints**: `cinema_source_assignments` and `screenings` have `REFERENCES ... ON DELETE CASCADE`.


## 2026-06-07

### v0.5.0

- **Screening Import Pipeline**: end-to-end `ImportScreeningsUseCase`.
- **Movie & Screening Repositories**: full repository/gateway stacks with upsert.
- **Source Adapter Architecture**: `SourceAdapter` protocol; adapters for Cinemacinema and CinemaPublic.
- **CinemaPublic Source Rewrite**: JSON-LD + AJAX fallback.
- **Interactive CLI**: `source import` with cinema selector, date picker, Rich table.
- **Richer Domain Model**: `Movie` tracks `directors`, `cast`, `description`, `duration_minutes`.


## 2026-06-06

### v0.4.0

- **Showtime Source Domain**: `SourceDefinition` and `CinemaSourceAssignment` entities, `SourceName` value object.
- **Source Management CLI**: register, delete, list, assign, unassign, query.
- **Dynamic Source Resolution**: `ShowtimeSource` protocol + `SourceRegistry`.
- **Cinemacinema Source**: first concrete source implementation.
- **Gateway Protocols**: `SourceDefinitionGateway`, `CinemaSourceAssignmentGateway`.
- **100% coverage** on all new code.

### v0.3.0

- **CLI Application**: Typer-based CLI with `auth` and `cinema` subcommands.
- **Authentication Flow**: `SupabaseAuthService` with email/password login, token refresh, session persistence.
- **Full Cinema CRUD**: create, list, update, delete via CLI.
- **Dependency Injection Container**: `Container` class manages lifecycle.
- **`website` Field**: added to `Cinema` entity and all layers.
- **Exception Isolation**: domain exceptions never leak past application layer.

### v0.2.0

- **Gateway Protocol Pattern**: `CinemaGateway` protocol decouples SQL from entity mapping.
- **Robust Error Handling**: `UniqueViolationError` → `GatewayError` → `CinemaIdAlreadyExistsError`.
- **Price Self-Validation**: `Price` validates non-negative in `__post_init__`.
- **Infrastructure Hardening**: `sanitize_dsn()` handles `@` in passwords; `load_dotenv()` deferred.

### v0.1.0

- **Domain Layer**: `Cinema`, `Movie`, `Screening` entities; value objects with validation.
- **Application Layer**: `CreateCinemaUseCase`, repository interface, application exceptions.
- **Interface Adapters**: `CinemaGateway` protocol, `SupabaseCinemaRepository`, `GatewayError`.
- **Infrastructure Layer**: `Database` (asyncpg pool), DSN sanitization, Supabase gateway.
- **Documentation**: `AGENTS.md`, MkDocs site, `docs/todo.md`, Supabase setup guide.
- **Testing**: 100% coverage across domain, application, and interface adapters.
