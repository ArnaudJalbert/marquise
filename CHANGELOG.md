# Changelog

All notable changes to this project are documented here, organized by date. The project is a
uv workspace with multiple packages — each entry notes which package(s) and version(s) were
affected.

Before 2026-07-15 the entire codebase shipped as a single package (`marquise`, now
`marquise-core`). Starting 2026-07-15, the FastAPI application lives in `marquise-api` and the
Typer CLI lives in `marquise-cli`, each with independent versions.

## 2026-07-29

### @marquise/components v0.1.0 + marquise-interface

- **Remove hardcoded filter options**: `filterOptions.ts` deleted. `FilterBar` now receives `cinemas`, `genres`, `languages` as props derived from the full dataset, so every option stays visible regardless of active client-side filters.
- **Widen `Genre` type from closed union to `string`**: genres come from free-text API data and cannot be enumerated statically. Added `paletteFamily(genre)` helper that falls back to `"sage"` for unknown genres.
- **`fetchMoviesByDate` per-date API fetching**: `PosterWallPage` only calls the API on date changes (`datesKey` stable dependency). All non-date filters (search, cinema, genre, lang, time range) are applied client-side via `useMemo`-wrapped `filterMovies` on the full cached dataset (`allMovies`), so toggling a filter is instant with no network round-trip.
- **Movie detail drawer**: receives the full `PosterMovie` object for instant header rendering from wall data. Screenings are lazy-fetched per-date via `fetchMovieScreenings(movieId, dateKey?)` — the API call only fires when the user switches dates.
- **Movie detail page (`/movie/:movieId`)**: standalone route that fetches movie metadata once (`fetchMovieInfo`) then per-date screenings on date change. Properly resets stale info on movie-to-movie navigation.
- **Remove dead API functions**: `fetchMovies` and `fetchMovieDetail` — superseded by `fetchMoviesByDate`, `fetchMovieInfo`, and `fetchMovieScreenings`. The old `MovieDetail` combined type removed accordingly.
- **Remove hardcoded `format` field**: `format: 'DCP'` was hardcoded across live API, mock API, mock data, and the `PosterMovie`/`MovieInfo` types — and never actually rendered, since the API does not yet expose a media-format field. Removed the field entirely from types, sources, and the two detail views.
- **Replace `PosterWallSkeleton` with loading spinner**: CSS-animated spinner replaces the skeleton placeholder (which did not correctly reflect grid layouts per view mode).
- `format` tag removed from `MovieDetailDrawer` and `MovieDetailPage` (the only two places it was rendered).
- `fetchMovieScreenings` and `fetchRawMovieScreenings` accept optional `dateKey` for per-day UTC-bounded queries.
- `deriveFilterOptions` memoized via `useMemo` in `PosterWallPage`.
- **Date pills replace prev/next arrows in detail views**: `MovieDetailDrawer` and `MovieDetailPage` now show horizontally scrolling date pills instead of prev/next arrow buttons. Dates are initially seeded from the wall's date-picker selection. A "More dates" button (`fetchMovieDates`) fetches the full list of available screening dates for the movie. Added `fetchMovieDates` to mock and live API layers.

### marquise-core v0.2.1

- **`CreateScreeningsCommand` updates on conflict instead of skipping**: when a `ScreeningAlreadyExistsError` is raised by `save()`, the command now calls `screening_repository.update()` to refresh the existing row. If the row disappears concurrently (`update` returns `None`), a new `ScreeningUpdateNotFoundError` is raised and the entry is counted as a skip.
- **Fix Cineplex ticket URL generation**: the gateway now prefers `session.ticketingRedesignUrl` and `session.ticketingUrl` from the API before falling back to the legacy deeplink construction. Removed the now-unused `film_url` parameter from `_build_ticket_url`.
- **Export `ScreeningUpdateNotFoundError`** from `marquise.application.exceptions`.

### marquise-api v0.1.5

- **Raise default rate limit from 60/min to 3000/min**: accommodates the frontend poster wall fetching many screenings per page load without hitting per-IP throttling.

## 2026-07-20

### marquise-core v0.2.0

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

### marquise-core v0.1.3

- **Standardise test structure across the test suite**: extracted `import_screenings` DTO
  validation tests into a dedicated file (`test_import_screenings_input_output_data.py`),
  moved `test_showtime_row.py` into `application/repositories/` to mirror the source layout,
  removed unused shared fixtures from `tests/conftest.py`, renamed 5 source gateway test
  files from `test_source.py` to `test_{source}_gateway.py`, and replaced 17 instances of
  explicit `AsyncMock(...)` wiring in controller tests with the idiomatic
  `.return_value = ...` pattern. All changes are test-only; no production code was modified.

## 2026-07-19

### marquise-api v0.1.4

- **Enable CORS for the deployed frontend**: sets `MARQUISE_API_CORS_ORIGINS = "https://marquise-interface.fly.dev"` in `apps/marquise-api/fly.toml`'s `[env]` block so browser requests from the deployed `marquise-interface` site are allowed against the production API (previously only `http://localhost:5173` was allowlisted, via the v0.1.1 change).

### marquise-interface

- **Fix Fly build failing to resolve workspace packages**: `web/apps/marquise-interface/fly.toml` had no `[build].context`, so flyctl defaulted it to the directory containing `fly.toml` (`web/apps/marquise-interface`) — too narrow for a Dockerfile that `COPY .`s the whole pnpm workspace and depends on sibling packages via `workspace:*`. Added `context = ".."` (relative to `fly.toml`, matching the config-relative resolution rule flyctl also applies to `dockerfile`) to point the build context at `web/`. The Dockerfile now also explicitly builds `@marquise/components` and `@marquise/api-client` (`pnpm --filter @marquise/components --filter @marquise/api-client build`) before `build:live-remote`, since those workspace packages need their own build output before the interface app can consume them.

## 2026-07-17

### marquise-api v0.1.3

- **Fix `flyctl deploy` failing on push to `main`**: flyctl resolves `[build].dockerfile` (and the CLI `--dockerfile` flag) relative to the directory containing `fly.toml`, not the repo root. `apps/marquise-api/fly.toml` still had `dockerfile = "apps/marquise-api/Dockerfile"` left over from the pre-move root-`fly.toml` setup, so flyctl looked for `apps/marquise-api/apps/marquise-api/Dockerfile` and failed with "not found". Changed it to `dockerfile = "Dockerfile"` and dropped the now-redundant `--dockerfile` flags from both `deploy-api` and `deploy-interface` jobs in `.github/workflows/fly-deploy.yml` (the interface job's fly.toml already had the correct relative path, but the CLI flag was overriding it with the same broken repo-rooted path).

### marquise-api v0.1.2

- **Move `fly.toml` into `apps/marquise-api/`**: colocated the Fly config with the Dockerfile it deploys instead of leaving it at the repo root, now that a second Fly app (`marquise-interface`) exists. The Dockerfile still requires repo-root build context (it reaches into `packages/marquise-core` and root `pyproject.toml`/`uv.lock`), so `.github/workflows/fly-deploy.yml` now invokes `flyctl deploy --config apps/marquise-api/fly.toml --dockerfile apps/marquise-api/Dockerfile` from the repo root rather than relying on the implicit root `fly.toml`.
- **`GET /v1/movies` gains bulk-by-ids lookup**: added a repeated `ids` query param (`?ids=a&ids=b`) alongside `?title=` — the two can be combined as an AND filter (movies whose id is in the list *and* whose title matches), or used independently. `ids` is capped at 100 per call (422 via `TooManyMovieIdsError` if exceeded) and additionally capped at the requested page `size` (`ids` count must not exceed `size`; 422 otherwise), and rejects `page != 1` (everything fits on one page by construction). IDs with no matching movie are silently omitted. No separate `/movies/by-ids` route — this reuses the same paginated `Page[MovieResponse]` response shape as the existing list endpoint. When both filters are given, the title match is applied in-memory to the `ids` lookup's results (no second SQL predicate).

### marquise-core v0.1.2

- **`MovieRepository.find_by_ids` reused by `ListMoviesUseCase`**: new Clean Architecture plumbing backing the bulk-by-ids mode of `GET /v1/movies` — `SupabaseMovieGateway.find_by_ids` (`WHERE id = ANY($1)`, the codebase's first multi-value SQL lookup), `MovieGateway` protocol, `SupabaseMovieRepository`. `ListMoviesUseCase.InputData` gained an `ids` field; when set, `execute()` branches to `find_by_ids` instead of the title/pagination `find_all` path. `MovieController.list` gained a matching `ids` parameter.

### marquise-interface

- **Add Fly.io deployment**: new `web/apps/marquise-interface/Dockerfile` (pnpm workspace build → static `nginx:alpine` serve, with SPA fallback via `nginx.conf`) and `fly.toml` (new Fly app `marquise-interface`). The production build runs in `live-remote` mode (`pnpm --filter marquise-interface build:live-remote`, a new package script), baking in `VITE_API_BASE_URL=https://marquise-api.fly.dev` so the deployed site serves real data.
- **CI**: `.github/workflows/fly-deploy.yml` now uses `dorny/paths-filter` to run independent `deploy-api` and `deploy-interface` jobs, each triggered only when its own app's files change on push to `main`.
- **Replace per-movie-id N+1 fetch with `getByIds`**: `liveApi.ts`'s poster-wall enrichment step previously issued one `GET /v1/movies/{id}` per distinct movie in the screenings window via `Promise.allSettled`. It now calls the new `client.movies.getByIds()` (chunked to 100 ids per request) instead, collapsing dozens of requests into one or a few.

### @marquise/api-client

- **Add `MoviesResource.getByIds`**: goes through `list()` with `ids` set and `size` forced to `ids.length` (satisfying the backend's `ids count <= size` constraint), unwrapping `.items` from the returned `Page`. `buildQuery` now serializes `string[]` values as repeated query params (`ids=a&ids=b`) to support it, and `ListMoviesParams` gained an `ids` field.

## 2026-07-15

### @marquise/components + marquise-interface

- **Move `filterMovies` filter/sort/dedup logic into `@marquise/components`**: extracted `filterMovies.ts` from `marquise-interface` into the shared component library so the AND-filter semantics (cinema, genre, date, language, time range, search text) and `mergeByTitle` cross-cinema dedup can be reused — and tested — in one place, not duplicated per app.
- **Add `addDaysToDateKey` to `@marquise/components/dateKey.ts`**: shared date-key arithmetic replaces an identically implemented private function in `liveApi.ts`.
- **Fix `PosterImage` render-time side effect**: replaced a `useState` + render-time mutation pattern with a canonical `useEffect` that resets the error state when `src` changes, eliminating a fragile anti-pattern.
- **Fix `PosterWallSkeleton` view-to-CSS mapping**: extracted the view→CSS-class lookup into a `VIEW_GRID_CLASS` config record instead of a chain of inline ternaries.
- **Consolidate `liveApi.ts` imports**: merged three separate `@marquise/components` import lines into one.
- **Add test infrastructure to `@marquise/components`**: added `vitest`, `jsdom`, and `@testing-library/react`; created `vitest.config.ts` and a `setup.ts` with jest-dom matchers and auto-cleanup.
- **30 unit tests across 5 test files**:
  - `dateKey.test.ts` — `toDateKey`, `parseDateKey`, `addDaysToDateKey` (round-trip, padding, month/year boundaries).
  - `genrePalette.test.ts` — every genre mapped to a palette family.
  - `PosterImage.test.tsx` — img rendering, error placeholder, src-change reset, custom className.
  - `PosterWall.test.tsx` — empty state, all four view modes render their grid.
  - `filterMovies.test.ts` — per-dimension filtering, time-range, search query, merge-by-title, screening dedup, partial-screening filtering after filter mismatch.

### marquise-core v0.1.1

- **Fix inconsistent showtime timezone handling across scraper sources**: `cinemapublic`, `cinemamoderne`, `cinemacinema`, and `cinematheque` were emitting naive Montreal-local `showtime` strings with no UTC offset, while `outremont` and `cineplex` already emitted genuinely UTC-aware timestamps — the two conventions were silently incompatible with each other and with any client reading `showtime` as real UTC. Added `marquise.infrastructure.sources._timezone.montreal_local_to_utc_iso()`, a shared `zoneinfo`-based (`America/Toronto`, DST-correct) conversion helper, and switched the four naive sources to call it so every source now emits a real, unambiguous UTC ISO 8601 `showtime`.
- **marquise-interface**: `formatShowtime`/`showtimeDateKey`/`resolveWindow` in `web/apps/marquise-interface/src/api/liveApi.ts` no longer assume `showtime` is a naive-local value mislabeled as UTC (the old `getUTCHours()` workaround) — they now convert real UTC to Montreal wall-clock time via `Intl.DateTimeFormat` (`America/Toronto`), matching the corrected backend contract. Added `montrealDateKeyToUtcRange()` to `web/apps/marquise-interface/src/timezone.ts` to resolve a Montreal calendar day to its real UTC start/end instants for the `/v1/screenings` date-range query.

### marquise-api v0.1.1

- **Enable CORS for local frontend dev**: sets `MARQUISE_API_CORS_ORIGINS = "http://localhost:5173"` in root `fly.toml`'s `[env]` block so browser requests from the local Vite dev server (both `marquise-admin` and `marquise-interface`, which default to port 5173) are allowed against the deployed API. `apps/marquise-api/src/marquise_api/app.py` already supported the env var; it was simply never set, so `CORSMiddleware` was never registered and all cross-origin requests were rejected.

### Docs

- **Replace text-based diagrams with Mermaid charts**: Converted ASCII box diagrams and arrow-chain data flows in `docs/architecture.md` and `docs/sources.md` to `flowchart` and `sequenceDiagram` Mermaid blocks. Enabled Mermaid rendering in MkDocs via `pymdownx.superfences` custom fence and CDN-loaded Mermaid JS. Also converted source mapping overview to `flowchart LR` and collapsed the API note ASCII box to plain text.

### marquise-core v0.26.0

- **Core public bootstrap API (#101, #102)**: adds a public bootstrap API for apps in `apps/` to depend on `marquise-core` without reaching into internal modules. New `MarquiseFactory` class in `packages/marquise-core/src/marquise/bootstrap.py` with lazy-loaded controller properties (`.cinema`, `.source`, `.auth`), `check_database_health()` method, and async context manager support. `create_factory()` async factory function and `create_factory_session()` async context manager for app integration. Public surface re-exported from `marquise/__init__.py` via `__all__`: `MarquiseFactory`, `create_factory`, `create_factory_session`, `CinemaController`, `SourceController`, `AuthController`. Import boundary enforcement: AST-based scanner (`tests/unit_tests/test_import_boundary.py`), `import-linter` contract in root `pyproject.toml`, and snapshot test (`tests/unit_tests/test_public_api.py`) prevents accidental `__all__` additions. Closes #101, #102.

### marquise-core v0.26.0, marquise-api v0.1.0, marquise-cli v0.1.0

- **Extract API and CLI into separate workspace packages**: FastAPI application code moved to `apps/marquise-api/` with `Depends(controller)` wiring from `marquise_api.dependencies` and CLI code to `apps/marquise-cli/` with `MarquiseFactory`. Added `MovieController` and `ScreeningController`. Removed delivery dependencies from `marquise-core`. Moved Dockerfile to `apps/marquise-api/`. Added Makefile with `test`, `api`, `cli`, `lint`, `format`, `ty` targets. Updated `docker-compose.yml` and `fly.toml` build paths. Closes #105, #106.

### marquise-core v0.25.1

- **Repo-root cleanup**: removes stale one-off tooling and planning artifacts left over from earlier work.
  - **`scripts/`**: removes the now-unneeded `inspect_screening_gateway.py` ad-hoc debug tool and the stale `migrate_001_initial_schema.py` runner (predated the columns/indexes added in migrations 002/003). Consolidates `001_initial_schema.sql`, `002_add_movie_screening_fields.sql`, and `003_screening_search_indexes.sql` into a single `scripts/marquise-schema.sql` representing the full, current `marquise` schema — run manually via the Supabase SQL Editor, same as before. Renames `001_test_schema.sql` to `scripts/marquise-test-schema.sql` to match. Updates `docs/sources.md`'s "Database Schema" section accordingly (it previously covered only migrations 001/002, missing 003 entirely).
  - **`bin/`**: removes `bench_list_cinemas.py`, `scrape_cinema.py`, and `scrape_cinemapublic.py` — one-off benchmarking/debug scripts predating the current source-adapter architecture, superseded by the `marquise source import` CLI command.
  - **`plan/`**: removes `feature-marquise-admin-scaffold-1.md`, a planning doc for work already merged (the `web/` monorepo scaffold).

### marquise-core v0.25.0

- **`web/` Turborepo monorepo scaffold (#64)**: bootstraps the admin web app toolchain skeleton as a pnpm + Turborepo workspace under `web/`, following the `apps/*` + `packages/*` convention so the repo can host multiple front ends under one CI pipeline. Adds the workspace root (`web/package.json`, `web/pnpm-workspace.yaml`, `web/turbo.json` with a `build`→`^build` pipeline), a bare Vite + React + TS admin app at `web/apps/marquise-admin`, and a shared `@marquise/core` package at `web/packages/core` (consumed via `workspace:*`, React as a peer dependency to avoid a duplicate runtime). The admin app renders a `CoreHello` smoke-test component from `@marquise/core` to prove the workspace wiring; `pnpm turbo run build` builds `core` before the app. No product logic, routing, API client, or UI kit yet — those are separate issues. Root `.gitignore` ignores `web/**/{node_modules,dist,.turbo,.env}`. The scope was broadened from issue #64's original single-app wording (see the issue's scope-update comment). Closes #64.
- **Web docs**: adds `web/README.md` (full monorepo how-to-run guide), per-workspace READMEs for `marquise-admin` and `@marquise/core`, and a `docs/web.md` page wired into the mkdocs nav.
- **README / docs refresh**: updates the root `README.md` and `docs/index.md` to reflect the current state — the REST API is built and deployed (not "planned"), all six showtime sources are listed (adds Théâtre Outremont), the CLI examples match the current interactive `source`/`import` commands, the env-var table covers the API rate-limit/log-level and CLI auth variables, and the Tech Stack lists the API and web front-end.
- **Théâtre Outremont (Ciné-Outremont) showtime source**: adds a new `outremont` source with **exact showtimes**. Rather than the public `/cinema/` listing (which shows only a date), it reads the venue's Tuxedo Billet ticketing backend directly over plain HTTP — the same Firebase Realtime Database the site's SPA uses — by replaying its bootstrap: read the public `configuration.json` for the Firebase config, sign in anonymously via the Identity Toolkit REST API, resolve the venue channel, then read the `shows` node. Each show carries an `events` map of `eventId → epoch-millis`, yielding one screening per event at its exact UTC instant (so e.g. Le Gâteau du président surfaces both its 16:00 and 19:30 screenings, not just a date). Shows are filtered to the `Cinéma` report-category. `fetch_movie_detail` reads a single show document and parses its paragraph-delimited description into `original_title`, `directors`, `cast`, `release_year`, `origin_countries`, `genres`, `duration_minutes`, `rating`, `poster_url`, and synopsis. Follows the existing single-venue pattern: `OutremontSource` gateway (`infrastructure/sources/outremont/`), `OutremontAdapter` (`interface_adapters/repositories/source_adapters/outremont.py`), registered as `"outremont"` in the DI container's `SourceRegistry`. Stdlib-only (`urllib` + `json` + `certifi`); no new dependencies.

### marquise-core v0.23.2

- **Drop redundant `OutputData` re-validation (#17)**: removes `__post_init__` checks on use-case `OutputData` fields that were already validated by the value they were copied from (a validated `CinemaId`/`SourceName`, or an entity/`InputData` field validated upstream) — e.g. `cinema_id`, `cinema_name`, `source_name`, `name`, `address`, `city`, `website` across `assign_source`, `create_cinema`, `create_source`, `delete_cinema`, `delete_source`, `get_cinema_source`, `import_screenings`, `list_cinemas`, `list_movies`, `list_registry_sources`, `list_sources`, `unassign_source`, and `update_cinema`. Keeps validation for genuinely computed/derived fields (e.g. `total`, `total_count`, `imported_count`, `updated_count`, `skipped_count`) where a bug in aggregation logic could otherwise produce an invalid value.

### marquise-core v0.23.1

- **Fix all `ty` type errors and promote to blocking CI check**: resolves 8 diagnostics across 5 files — exception handler signature mismatches in `infrastructure/api/app.py` and `exception_handlers.py`, nullable `expires_at` in `infrastructure/auth/supabase_auth_service.py`, missing `urllib.error` import and untyped assignment in `infrastructure/sources/cinemacinema/gateways/source.py`, and list narrowing issue in `infrastructure/sources/cineplex/gateways/source.py`. Promotes `ty check` to a blocking CI step (was `continue-on-error: true`).

## 2026-07-13

### marquise-core v0.23.0

- **`GET /cinemas/{cinema_id}` single-cinema endpoint (#63)**: adds a new read-only endpoint returning a single cinema by its ID (`id`, `name`, `address`, `city`, `website`), enabling the admin web app's cinema detail page to show the cinema's own metadata without pulling its showtimes. Backed by a new `GetCinemaUseCase` mirroring the existing `GetMovieUseCase` pattern — validated `InputData`/`OutputData`, uses `CinemaRepository.find_by_id`, raises `CinemaNotFoundError` (404) for unknown IDs. Cached and rate-limited per the existing read-endpoint conventions. Closes #63.

### marquise-core v0.22.0

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

### marquise-core v0.21.2

- **Fix Cineplex Royalmount import failure**: adds missing `location_id` mapping for "Cinéma Cineplex Royalmount".
- **Fix Cinéma Cinéma import crash on unknown release year**: `_extract_release_year()` guards against `annee: 0`.
- **Live integration coverage for newly onboarded cinemas (#83-#86)**.

### marquise-core v0.21.1

- **Post-deploy verification and docs for Fly.io production deployment**: smoke-tested live API; documents production URL; automated smoke-test step in CI. Closes #123.

## 2026-07-11

### marquise-core v0.21.0

- **Docker image + Compose for the read-only API**: multi-stage Dockerfile, `.dockerignore`, `docker-compose.yml`, `.env.example`. Closes #119.

### marquise-core v0.20.0

- **Structured JSON request logging**: `JsonFormatter` (stdlib `logging.Formatter`), `RequestLoggingMiddleware`, per-request `X-Request-ID` header, `ErrorResponse.request_id` field. Configurable via `MARQUISE_API_LOG_LEVEL`. Closes #55.

### marquise-core v0.19.0

- **Polished OpenAPI docs**: expanded `FastAPI(description=...)`, `json_schema_extra` examples, field-level descriptions, `error_responses()` helper. Closes #57.

### marquise-core v0.18.0

- **DB-aware readiness check (`GET /ready`)**: `Database.ping()`, `Container.check_database_health()`, `GET /ready` → 200/503. Closes #56.

### marquise-core v0.17.0

- **Global exception handlers**: `exception_handlers.py` with `_APPLICATION_ERROR_MAPPING`, `ValueError` handler (422), catch-all `Exception` handler (500, never leaks message). `ErrorResponse` schema. Closes #51.

### marquise-core v0.16.0

- **`GET /movies` list/search endpoint**: `title` filter, `ListMoviesUseCase`, `MovieRepository.find_all`. Closes #53.

## 2026-07-09

### marquise-core v0.15.0

- **API versioning (`/v1` prefix)**: all routes except `/health` mounted under `/v1`. Closes #54.

### marquise-core v0.14.0

- **Per-IP rate limiting**: slowapi, 60 req/min default, configurable via `MARQUISE_API_RATE_LIMIT`. Closes #50.

### marquise-core v0.13.0

- **CORS support**: `CORSMiddleware` when `MARQUISE_API_CORS_ORIGINS` is set. Closes #52.

### marquise-core v0.12.0

- **SQL-level pagination**: LIMIT/OFFSET + `COUNT(*) OVER()` in gateways; fastapi-pagination `Page`/`Params`.

### marquise-core v0.11.0

- **New source: Cinéma Moderne**: scraper for Cinéma Moderne schedule pages. Closes #48.

### marquise-core v0.10.1

- **Cineplex import no longer aborts on `external_id` collision**: per-row skip via `return_exceptions=True`.

### marquise-core v0.10.0

- **New source: Cinémathèque québécoise**: OmniWeb ticketing portal scraper. Closes #47.

### marquise-core v0.9.1

- **In-memory response caching**: fastapi-cache2 `@cache()` with 1h TTL, configurable.
- **Fix caching date range bug**: default `from`/`to` resolved before caching.
- **Default date range now UTC and timezone-aware**.
- **Mixed aware/naive `from`/`to` no longer 500s**.

## 2026-06-27

### marquise-core v0.9.0

- **Read-only public REST API (FastAPI)**: endpoints for cinemas, showtimes, movies, plus health probe. New `GetMovieUseCase`, `GetCinemaShowtimesUseCase`. `create_app()` factory. Closes #20.

### marquise-core v0.8.2

- **Deduplicate movies by normalized title**: case-insensitive `WHERE LOWER(title)` match; white-space normalization. Closes #23.

### marquise-core v0.8.1

- **Fix daily scheduled import failures**: English name alias for Scotiabank; dedup on `external_id`.

### marquise-core v0.8.0

- **Scheduled / bulk import path**: `marquise import all --days N`, cron workflow. `import_commands.py`. Closes #22.
- **Deduplicate Cineplex showtimes before upsert**.
- **Cineplex subscription key rotation**: `_discover_subscription_key` helper.

### marquise-core v0.7.11

- **Smaller cleanups batch (#24)**: shared fixtures, async import hoisting, dead helper cleanup, `GatewayError` move, Google-style docstring conversion, datetime parsing cleanup.

### marquise-core v0.7.10

- **Replace gateway `dict` + `__inserted` with typed `SaveOutcome`**. Closes #18.

### marquise-core v0.7.9

- **Validate `ShowtimeRow` at the scraper boundary**: reject empty titles, naive datetimes. Closes #19.

### marquise-core v0.7.8

- Remove the old OpenCode plan that was accidentally published.

### marquise-core v0.7.7

- **Add `ty` type checker (non-blocking CI rollout)**. Closes #34.

### marquise-core v0.7.6

- **Stop mutating `Movie` in place during enrichment**: pure function via `dataclasses.replace()`. Closes #14.
- **Standardize on `str | None` over `Optional[str]`**: Ruff `UP` rule. Closes #16.

### marquise-core v0.7.5

- **Fix misleading `updated_count` documentation and CLI labels**. Closes #15.

### marquise-core v0.7.4

- **Rewrote `AGENTS.md`** from 1,434 lines to ~390 lines. Closes #6.
- **Created `ARCHITECTURE.md`**: ~120-line document describing the actual system.
- **Updated `CONTRIBUTING.md`** with self-contained setup and CI pipeline.

## 2026-06-26

### marquise-core v0.7.3

- **Removed vestigial domain code**: deleted domain exceptions package, unused value objects, and their test files. Closes #9.

### marquise-core v0.7.2

- **Fix SSL verification in scrapers**: removed `ssl._create_unverified_context()`. Closes #8.

### marquise-core v0.7.1

- **CI Pipeline**: `.github/workflows/ci.yml` — quality + integration jobs. Closes #7.
- **Coverage gate**: `fail_under = 80` in pyproject.toml.

## 2026-06-22

### marquise-core v0.7.0

- **Cineplex Source**: scraper for 8 Montreal-area theatres.
- **Movie Enrichment Pipeline**: parallel enrichment from Cineplex, Cinemacinema, Cinema Public.
- **Screening Metadata**: `external_id`, `ticket_url`, `room`, `language` fields.
- **Movie Schema Revamp**: `release_date` → `release_year`; 6 new enrichment columns.
- **Domain changes**: `Movie` enrichment fields, `Screening` metadata, `Price` validation.
- **Infrastructure**: migration 002, gateway `update()`, DI container wiring.

## 2026-06-10

### marquise-core v0.6.0

- **Screening entity refactor**: full `Movie`/`Cinema` object references; `price`, `available_seats`, `is_sold_out` removed.
- **CinemaSourceAssignment refactor**: full entity references instead of IDs.
- **Use cases simplified**: no longer depend on `SourceDefinitionRepository`.
- **Joined queries**: all gateway `find_by_*` use SQL JOINs with prefixed aliases, eliminating N+1 lookups.
- **FK constraints**: `cinema_source_assignments` and `screenings` have `REFERENCES ... ON DELETE CASCADE`.

## 2026-06-07

### marquise-core v0.5.0

- **Screening Import Pipeline**: end-to-end `ImportScreeningsUseCase`.
- **Movie & Screening Repositories**: full repository/gateway stacks with upsert.
- **Source Adapter Architecture**: `SourceAdapter` protocol; adapters for Cinemacinema and CinemaPublic.
- **CinemaPublic Source Rewrite**: JSON-LD + AJAX fallback.
- **Interactive CLI**: `source import` with cinema selector, date picker, Rich table.
- **Richer Domain Model**: `Movie` tracks `directors`, `cast`, `description`, `duration_minutes`.

## 2026-06-06

### marquise-core v0.4.0

- **Showtime Source Domain**: `SourceDefinition` and `CinemaSourceAssignment` entities, `SourceName` value object.
- **Source Management CLI**: register, delete, list, assign, unassign, query.
- **Dynamic Source Resolution**: `ShowtimeSource` protocol + `SourceRegistry`.
- **Cinemacinema Source**: first concrete source implementation.
- **Gateway Protocols**: `SourceDefinitionGateway`, `CinemaSourceAssignmentGateway`.
- **100% coverage** on all new code.

### marquise-core v0.3.0

- **CLI Application**: Typer-based CLI with `auth` and `cinema` subcommands.
- **Authentication Flow**: `SupabaseAuthService` with email/password login, token refresh, session persistence.
- **Full Cinema CRUD**: create, list, update, delete via CLI.
- **Dependency Injection Container**: `Container` class manages lifecycle.
- **`website` Field**: added to `Cinema` entity and all layers.
- **Exception Isolation**: domain exceptions never leak past application layer.

### marquise-core v0.2.0

- **Gateway Protocol Pattern**: `CinemaGateway` protocol decouples SQL from entity mapping.
- **Robust Error Handling**: `UniqueViolationError` → `GatewayError` → `CinemaIdAlreadyExistsError`.
- **Price Self-Validation**: `Price` validates non-negative in `__post_init__`.
- **Infrastructure Hardening**: `sanitize_dsn()` handles `@` in passwords; `load_dotenv()` deferred.

### marquise-core v0.1.0

- **Domain Layer**: `Cinema`, `Movie`, `Screening` entities; value objects with validation.
- **Application Layer**: `CreateCinemaUseCase`, repository interface, application exceptions.
- **Interface Adapters**: `CinemaGateway` protocol, `SupabaseCinemaRepository`, `GatewayError`.
- **Infrastructure Layer**: `Database` (asyncpg pool), DSN sanitization, Supabase gateway.
- **Documentation**: `AGENTS.md`, MkDocs site, `docs/todo.md`, Supabase setup guide.
- **Testing**: 100% coverage across domain, application, and interface adapters.
