---
type: research
status: complete
owner: Aster
date: 2026-08-29
reviewed_revision: f0ff451d3ea9f3ed4f4e5d4243bdc04129ab8f53
---

# Marquise Architecture and Performance Audit

**Date:** 2026-08-29
**Revision reviewed:** `f0ff451d3ea9f3ed4f4e5d4243bdc04129ab8f53` (`main`)
**Scope:** all tracked backend, API, CLI, scraper, SQL, web, deployment, test, CI, and architecture files in `ArnaudJalbert/marquise`

## Executive conclusion

Marquise already has a sound high-level dependency direction: an AST scan of every Python module found **zero outward layer dependencies**, and the backend/web public boundaries are mostly clear. The best improvements are not a rewrite. They are concentrated in the import pipeline, source boundary, persistence model, and listings read path.

Recommended order:

1. **Create one application-level import workflow with bounded concurrency and batch persistence.**
2. **Replace blocking scraper I/O hidden behind `async def`.**
3. **Redesign the source registry as an immutable, typed source catalog and persist per-cinema source bindings.**
4. **Correct movie and screening identity constraints before the dataset grows.**
5. **Add a listings projection endpoint so the web app does not reconstruct a page through up to 11 requests.**
6. **Align the screening index and pagination strategy with the primary date-range query.**
7. Add static delivery caching/compression and make architecture/build checks real CI gates.

These changes reinforce the existing Clean Architecture rather than weakening it.

---

## Priority findings

### P0 — The import workflow belongs in the application layer and needs batch persistence

**Evidence**

- Both CLI paths independently orchestrate fetch → movie reconciliation → title-to-ID mapping → screening persistence:
  - `apps/marquise-cli/src/marquise_cli/import_commands/all_command.py:72-158`
  - `apps/marquise-cli/src/marquise_cli/import_commands/cinema_command.py:57-116`
- Movie writes are one coroutine/database operation per missing movie: `packages/marquise-core/src/marquise/application/use_cases/create_missing_movies.py:116-124`.
- Screening writes are one coroutine per row, with an exception-driven second query for existing rows: `packages/marquise-core/src/marquise/application/use_cases/create_screenings.py:105-177`.
- Each gateway operation independently acquires a pool connection; the pool has only five connections: `packages/marquise-core/src/marquise/infrastructure/supabase/database.py:61-64`, `.../supabase/gateways/screening.py:110-157`, `187-207`.
- `run_import_all` starts every cinema at once with no concurrency limit: `apps/marquise-cli/src/marquise_cli/import_commands/all_command.py:156-158`.

**Why it matters**

- Delivery contains business orchestration, so another delivery mechanism would need to duplicate it.
- A cinema import performs **O(movies + screenings)** database round trips and can saturate the five-connection pool with queued tasks.
- A failure can leave a partial cinema import: movies and some screenings may be committed while later rows fail.
- Exceptions are used as the normal “row already exists” branch, adding a second round trip for updates.

**Recommendation**

Add an application use case such as `ImportCinemaScheduleCommand` that owns the complete per-cinema workflow. Keep the all-cinemas loop in delivery, but make it call this single use case.

Expose batch-oriented application ports, for example:

- `MovieRepository.reconcile_many(...)`
- `ScreeningRepository.upsert_many(...)`
- or one purpose-built `CinemaScheduleImportRepository` returning an import result

Implement the infrastructure side with one transaction per cinema and set-based PostgreSQL (`UNNEST`, staging rows, or multi-row `INSERT ... ON CONFLICT DO UPDATE`). Deduplicate before persistence. Bound cinema/source concurrency explicitly rather than letting task count determine pressure.

**Acceptance signal**

- One application call imports one cinema.
- Single-cinema and bulk CLI paths contain no reconciliation/mapping logic.
- Query count is constant or chunk-bounded per cinema rather than per row.
- A forced mid-import failure leaves no partial screening batch.

---

### P0 — All seven source gateways expose async APIs while performing blocking network work

**Evidence**

The seven provider modules use synchronous `urllib.request.urlopen` and/or synchronous `ThreadPoolExecutor` collection inside methods exposed as `async def`:

- `cinemacinema/gateways/source.py:143-160`, `270-397`, `399-431`
- `cinemamoderne/gateways/source.py:250-289`, `340-380`
- `cinemapublic/gateways/source.py:370-455`, `559-607`
- `cinematheque/gateways/source.py:195-257`, `294-340`
- `cineplex/gateways/source.py:338-412`
- `cinestarz/gateways/source.py:82-103`, `140-157`
- `outremont/gateways/source.py:455-499`

For example, `CinemaCinemaSource.fetch_showtimes()` directly calls synchronous `_fetch_schedule()` at `cinemacinema/gateways/source.py:311`, and `CineplexSource.fetch_showtimes()` directly calls `_fetch_json()` at `cineplex/gateways/source.py:388-392`.

The application then assumes these operations are non-blocking and gathers movie-detail requests concurrently: `application/use_cases/fetch_screenings_from_source.py:125-152`. Bulk import similarly gathers cinemas: `all_command.py:156-158`.

**Why it matters**

The event loop is blocked during scraper HTTP and while synchronous executor contexts wait for results. The apparent concurrency in the application is therefore unreliable; one slow source can stall unrelated cinema tasks. Detail enrichment can also launch an unbounded number of outbound requests when the transport is made truly asynchronous.

Some providers also refetch data already fetched for showtimes. Cinémathèque loads each date page for showtimes (`cinematheque/gateways/source.py:217-257`) and then fetches the same date page again for each movie identifier (`329-340`).

**Recommendation**

Create an injected async HTTP transport owned by infrastructure, with:

- connection reuse
- explicit connect/read/total timeouts
- bounded per-host concurrency
- retry policy only for safe transient failures
- request-scoped response caching where one page supplies multiple films

Use it in every provider gateway. A safe first increment is to wrap each complete blocking provider call in `asyncio.to_thread`, but that is transitional: it does not provide connection pooling or principled request limits.

Have source gateways return schedule and available enrichment together when the upstream response already contains both. Otherwise provide a batch enrichment method so one source can coalesce requests by page/date.

**Acceptance signal**

A test with one deliberately slow provider does not block an independent coroutine timer or another provider. Maximum in-flight source requests is configured and tested.

---

### P0 — The source registry is doing three jobs and the cinema-to-provider binding is brittle

**Evidence**

`SourceRegistry` currently:

1. acts as a mutable service locator (`register`, `_adapters`): `interface_adapters/repositories/source_registry.py:46-80`;
2. dispatches runtime calls by string key: `82-115`, `137-156`;
3. validates and normalizes raw provider dictionaries into application DTOs: `116-135`, `159-181`.

The source protocol does not enforce real signatures or output types. It deliberately uses `*args`, `**kwargs`, and `Any`: `interface_adapters/repositories/protocols/showtime_source.py:13-52`. `SourceAdapter` also returns raw dictionaries: `source_adapters/base.py:11-50`.

The DI file has a parallel hard-coded import/registration list: `infrastructure/di/source_registry.py:5-56`. Persistent source definitions are a second catalog (`scripts/marquise-schema.sql:17-28`), while `CreateSourceUseCase` only validates database uniqueness (`application/use_cases/create_source.py:63-95`) and assignment validates only persistent existence (`assign_source.py:94-126`).

Provider venue IDs are keyed by mutable display names in source adapters:

- Cineplex: `source_adapters/cineplex.py:17-29`, `68-76`
- Cinéma Cinéma: `source_adapters/cinemacinema.py:17-21`, `56-61`
- Cinema Public: `source_adapters/cinemapublic.py:17-21`, `56-68`
- Cine Starz: `source_adapters/cinestarz.py:13-16`, `37-44`

`CinemaSourceAssignment` stores only cinema and source, not the provider venue key: `domain/entities/cinema_source_assignment.py:11-21`; the SQL table likewise stores only `cinema_id` and `source_name`: `scripts/marquise-schema.sql:23-28`.

**Why it matters**

- Renaming a cinema can silently break imports.
- Adding one source requires synchronized edits across distant folders, DI, database registration, and tests.
- Raw dicts delay validation until a central registry that knows every provider field.
- The mutable registry is unnecessary after startup and makes invalid intermediate states possible.
- Code-level availability and database-level registration can drift.

**Recommendation**

Keep the Clean Architecture layers, but make each provider a mirrored vertical slice:

```text
interface_adapters/sources/<provider>/adapter.py
infrastructure/sources/<provider>/http.py
infrastructure/sources/<provider>/parser.py
infrastructure/sources/<provider>/gateway.py
```

Do not split small providers mechanically; split the current 341–608-line modules where transport, parsing, and orchestration are already distinct responsibilities.

Change the application boundary so each adapter returns typed `ShowtimeRow` and `MovieEnrichmentData` directly. Give each concrete gateway/adapter a specific protocol instead of the wildcard `ShowtimeSource` protocol.

Construct an immutable catalog in one call:

```python
SourceCatalog({SourceName("cineplex"): cineplex_adapter, ...})
```

The catalog should only list capabilities and dispatch. Duplicate-key validation happens in its constructor; there is no public mutation after composition.

Add a `source_venue_key` (string) to `CinemaSourceAssignment` and its table. Provider adapters consume that stable key instead of matching `Cinema.name`. Validate assignment against both the persistent source definition and code catalog. Treat code as authoritative for implementation availability; keep database metadata for operator-facing labels/configuration.

**Acceptance signal**

- Renaming a cinema does not affect import routing.
- A provider adapter cannot compile/type-check if it returns an invalid row shape.
- Adding a provider has one composition entry and one mirrored provider slice, without modifying registry logic.
- An unavailable code provider cannot be assigned from persisted metadata.

---

### P1 — Database identity constraints contradict application identity rules

**Evidence**

Movies are globally unique by exact title: `scripts/marquise-schema.sql:30-44`. Persistence upserts on title and overwrites metadata: `infrastructure/supabase/gateways/movie.py:71-118`. The integration test explicitly expects a second movie with the same title and a different year to overwrite the first: `tests/integration_tests/infrastructure/supabase/gateways/test_movie_gateway_integration.py:94-116`.

The application does the opposite: it treats the same canonical title with a conflicting release year as a new movie: `application/use_cases/create_missing_movies.py:175-198`, tested at `tests/unit_tests/application/use_cases/test_create_missing_movies.py:186-203`.

Screening `external_id` is described as source-native (`application/repositories/source_registry_query.py:35-50`) but is globally unique with no source column: `scripts/marquise-schema.sql:46-58`. All providers therefore share one identifier namespace.

Movie discovery uses `%term%` searches for every broad title term: `infrastructure/supabase/gateways/movie.py:169-185`. The schema has no normalized-title or trigram index.

**Why it matters**

- Remakes and unrelated films sharing a title cannot be represented consistently.
- Import behavior differs between mocked application tests and the real database.
- Source-native numeric/string IDs can collide across providers.
- Wildcard matching will become the dominant reconciliation cost as the movie table grows.

**Recommendation**

Decide and encode explicit identities:

- add a normalized `title_key` column;
- use a uniqueness rule that includes release year when known, with a documented unknown-year policy;
- optionally add a source alias table (`source_name`, `source_movie_id` → `movie_id`) so reconciliation does not depend on fuzzy titles;
- persist `source_name` on screenings/import records and scope external-ID uniqueness to the source (and venue if the upstream namespace requires it).

Index the actual lookup key. If substring search remains user-facing, add `pg_trgm` and a GIN/GiST trigram index; do not add it solely for reconciliation if exact normalized keys replace that query.

**Acceptance signal**

An integration test can store two same-title films from different years without overwrite, and two providers can use the same external ID without collision.

---

### P1 — The web listings page rebuilds a read model through a network waterfall

**Evidence**

For one date, the client:

1. fetches screening pages sequentially in chunks of 100: `web/packages/marquise-client/src/http-client.ts:124-162`;
2. then fetches movie records in sequential chunks: `164-175`;
3. then fetches cinema websites: `177-198`;
4. only then creates grid items: `71-92`.

With the configured 500-screening cap and up to 500 distinct movies, that path can require **11 HTTP requests** before the page model is complete.

The database query already joins full movie and cinema rows: `infrastructure/supabase/gateways/screening.py:18-45`, `283-329`. The application screening DTO discards most joined movie/cinema data: `application/use_cases/search_screenings.py:186-201`, forcing the browser to request it again.

Client requests are not abortable (`http-client.ts:256-262`); `useMovieFilters` only ignores stale responses after they complete: `web/packages/components/src/components/movie/use-movie-filters.ts:190-228`. Date results are not cached, so back-and-forth date navigation refetches them.

The browser's most expensive endpoint also bypasses the configured API response cache: `apps/marquise-api/src/marquise_api/routers/screenings.py:23-29`. This is intentional enough to be locked by `apps/marquise-api/tests/test_api.py:1250-1263`, while comparable movie endpoints use `@cache()`.

**Why it matters**

This adds avoidable round trips, repeated JSON/Pydantic/domain mapping, and database work on the critical path. Repeated identical listing URLs currently repeat that database work as well. A server cache can reduce backend work, but it cannot remove browser-to-server latency or the multi-request waterfall.

**Recommendation**

Use the architecture’s documented read-adapter pattern for a purpose-built listings projection. Add a date-range endpoint that returns movie cards already grouped with showtimes and cinema links in one response. Query only the fields the grid needs and avoid constructing full domain aggregates for this display-only path.

Add an `AbortSignal` to the client protocol and cancel stale date loads. Add a small in-memory promise/result cache keyed by date (with explicit invalidation/TTL aligned to import freshness).

Cache the purpose-built listings response with an explicit freshness policy. A short TTL is the smallest change; an import-generation key or invalidation signal is preferable if newly imported showtimes must become visible immediately. If the generic `/v1/screenings` endpoint remains uncached for freshness, document that trade-off rather than relying on an unexplained decorator omission.

Keep detailed movie and screening endpoints for their own routes; do not make the generic endpoints serve every UI shape.

**Acceptance signal**

The first listings render uses one API request, changing dates aborts superseded work, returning to a recently viewed date does not refetch within the browser cache window, and repeated server requests follow the documented freshness/cache policy.

---

### P1 — The primary screening query lacks its matching index and repeats full-result counts

**Evidence**

The web’s main listings request filters all cinemas by only a showtime range: `web/packages/marquise-client/src/http-client.ts:124-129`. The screening query then filters and orders by showtime: `packages/marquise-core/src/marquise/infrastructure/supabase/gateways/screening.py:274-277`, `300-313`.

The schema has indexes on `movie_id`, `(cinema_id, showtime)`, and `(movie_id, showtime)`, but no showtime-leading index: `scripts/marquise-schema.sql:60-67`. PostgreSQL cannot use the trailing `showtime` portion of those composite indexes efficiently when the leading cinema/movie column is absent.

Every paginated page also computes `COUNT(*) OVER()` across the full joined result before applying the limit: `screening.py:298-329`. The current web client requests screening pages sequentially, so a 500-row date can repeat that exact count five times. Ordering is only `ORDER BY s.showtime` (`screening.py:307`), which is not deterministic for rows sharing a showtime under offset pagination.

**Why it matters**

As screenings accumulate, the primary page can scan/sort more data than necessary and redo exact-count work for every page. Offset pagination also becomes slower on deep pages and can duplicate/skip rows if data changes between requests.

**Recommendation**

The listings projection endpoint is the first fix because it removes this pagination loop entirely. For the generic screenings API:

- validate with `EXPLAIN (ANALYZE, BUFFERS)` on production-shaped data;
- add a showtime-leading index such as `(showtime, id)` if the plan confirms the expected scan/sort;
- make ordering deterministic with `ORDER BY s.showtime, s.id`;
- offer cursor pagination on `(showtime, id)` and omit exact totals where clients do not use them;
- retain the current page/total contract only where compatibility requires it.

Review whether `idx_screenings_movie_id` is redundant after checking index usage, since `(movie_id, showtime)` already has the same leading key.

---

### P2 — Static delivery leaves easy transfer and repeat-visit savings unused

**Evidence**

The production web build is a single hashed JS bundle of **343.36 kB / 107.12 kB gzip** and CSS of **30.43 kB / 6.60 kB gzip**. The Nginx configuration only defines SPA fallback: `web/apps/marquise-interface/nginx.conf:1-11`. It does not enable compression or immutable caching for hashed assets.

The app currently ships one route bundle (`web/apps/marquise-interface/src/App.tsx:1-349`); the movie-detail component is imported eagerly at `App.tsx:3-11` even though only one route is shown at a time.

`MoviePoster` always emits `loading="lazy"` and `fetchPriority="low"` (`web/packages/components/src/components/movie/MoviePoster.tsx:46-54`), including the prominent direct-route poster in `MovieDetailPage.tsx:385-390`. That can deprioritize a likely largest-contentful-paint image.

**Recommendation**

First configure Nginx to:

- gzip or Brotli compress JS/CSS/JSON/SVG;
- serve `/assets/*` with `Cache-Control: public, max-age=31536000, immutable`;
- serve `index.html` with no-cache/revalidation.

Only add route-level lazy loading for `MovieDetailPage` if bundle analysis shows a meaningful split after compression. At the current 107 kB gzip total, caching/compression is higher leverage than component-level micro-optimization.

Expose image loading/fetch-priority props on `MoviePoster`: retain lazy/low for grid cards and use eager/high for the detail hero.

---

### P2 — Architecture and web quality checks are documented but not fully enforced

**Evidence**

- `CONTRIBUTING.md:286-300` says the quality job runs import-boundary enforcement, but `.github/workflows/quality.yml:29-44` runs format, Ruff, ty, and only core unit tests.
- API and CLI test suites are not run by the quality workflow, despite `CONTRIBUTING.md:163-173` defining them as part of `make test`.
- No web lint/typecheck/test/build job exists in the quality workflow.
- The import-linter contract at `pyproject.toml:43-56` is not executed in CI and currently fails locally with `Module 'apps' does not exist`. The unit test only checks that the contract text exists (`tests/unit_tests/test_import_boundary.py:75-80`); the AST scanner does enforce the specific apps → core-private boundary.
- A full parallel `pnpm test` run produced one timing failure in `marquise-interface/src/App.test.tsx:87`; the isolated package rerun passed all 14 tests, indicating a load-sensitive test rather than a confirmed product defect.

**Why it matters**

Architectural and performance-sensitive web changes can deploy from `main` without the repository’s own web quality gates. A dead configuration creates false confidence.

**Recommendation**

Add independent CI jobs for:

- API and CLI tests;
- web install + lint + typecheck + test + production build;
- an executable import-boundary check.

Either fix the import-linter package model and run it, or remove it and expand the AST boundary test to enforce all Python layer directions. Add a web import-boundary rule (package → app and deep imports). Keep jobs parallel so stronger coverage does not lengthen the critical path unnecessarily. Stabilize the load-sensitive app test before making workspace-parallel tests mandatory.

---

## Proposed target shape

```text
Delivery
  CLI import one/all
      ↓
Application
  ImportCinemaScheduleCommand
  SourceCatalog port (typed, immutable)
  Batch import repository / unit-of-work port
      ↓
Interface adapters
  sources/<provider>/adapter.py      # CinemaSourceBinding → typed rows
  read_models/listings.py            # display projection
  repositories/...                   # domain persistence mapping
      ↓
Infrastructure
  sources/<provider>/http.py         # injected async transport
  sources/<provider>/parser.py       # pure parsing
  sources/<provider>/gateway.py      # provider orchestration
  postgres/batch_import.py           # transaction + set-based upserts
  postgres/listings_query.py         # purpose-built read query
```

The source catalog should be code-level and immutable. Persistent `source_definitions` remain operator-facing metadata. `cinema_source_assignments` should contain the stable provider venue key required to call the source.

---

## Sequenced roadmap

### Phase 1 — Make behavior safe and measurable

1. Add import instrumentation: per-source HTTP request count/duration, rows fetched, rows inserted/updated/skipped, and per-cinema elapsed time.
2. Add source concurrency limits and move blocking calls off the event loop as a transitional fix.
3. Add integration tests for same-title/different-year movies and cross-provider external-ID reuse.
4. Fix CI so backend apps and web checks gate changes.

### Phase 2 — Consolidate the import architecture

1. Introduce `ImportCinemaScheduleCommand` and move duplicated orchestration out of CLI.
2. Add stable `source_venue_key` to assignments and migrate hard-coded name maps.
3. Make source outputs typed at each adapter; make the catalog immutable.
4. Split large provider modules by transport/parser/orchestration where justified.

### Phase 3 — Remove the largest performance costs

1. Implement batch movie reconciliation and screening upsert in one transaction per cinema.
2. Replace blocking transports with a shared injected async HTTP client and coalesced/batch enrichment.
3. Add the listings projection endpoint, browser cancellation, a short-lived browser date cache, and an explicit server freshness/cache policy.
4. Validate the primary screening query plan, add a showtime-leading index where confirmed, and introduce deterministic cursor pagination where exact totals are unnecessary.
5. Add Nginx compression and immutable hashed-asset caching.

---

## Verification performed

- Fresh clone of `main` at `f0ff451d3ea9f3ed4f4e5d4243bdc04129ab8f53`.
- Inventory: 423 tracked files; 292 `.py` files and 59 `.ts`/`.tsx` files; approximately 22,954 code lines reported by `pygount` after duplicate/generated classification.
- Programmatic AST scan of every core Python module: zero outward dependency-direction violations.
- Python checks:
  - Ruff format: passed
  - Ruff lint: passed
  - ty: passed
  - core unit tests: **566 passed**
  - API tests: **84 passed**
  - CLI tests: **69 passed**
- Web checks:
  - lint: passed
  - typecheck: passed
  - client tests: **37 passed**
  - isolated interface tests: **14 passed**
  - production build: passed
  - full parallel workspace test run had one load-sensitive interface failure; isolated rerun passed
- Production web bundle measured from the real Vite build:
  - JS: 343.36 kB / 107.12 kB gzip
  - CSS: 30.43 kB / 6.60 kB gzip
- `uv run lint-imports` was executed and failed because the configured `apps` module is not importable by import-linter.

## Changes not recommended now

- Do **not** replace the existing Clean Architecture with a flatter “scrapers folder”; dependency direction is currently healthy.
- Do **not** introduce dynamic plugin discovery or entry points for seven known in-repo sources. An explicit immutable composition map is simpler and sufficient.
- Do **not** add a distributed cache while the API runs one machine. First optimize the listings read shape and static caching; revisit shared caching only when horizontal API scaling is real.
- Do **not** split every provider into many tiny files. Split only transport, pure parsing, and orchestration when a module’s current size/mixed responsibilities justify it.
