# Production browsing slice, issue #333

This implements the first batch of Screenings and Movies. It does not complete
#334 through #338, merge, deploy, or claim live catalogue verification.

## Design and contract

Reuse the approved #332 layout and its Helvetica typography. Keep white #fff,
black #000, grey borders #ddd and neutral missing-poster fill #f2f2f2. Original
poster colors remain intact. Keep four desktop columns, two mobile columns,
bounded titles, and previews attached immediately below their cards. The initial
Screenings slice shows today's Montreal date. Additional controls follow in
#335. The Movies search remains full-width with an accessible name and no visible
label. No hero, heading above Screenings, or new design treatment was added.

The new `GET /v1/screening-movies` endpoint accepts inclusive Montreal `start`
and `end` dates and a one-based `page`. Its size is fixed at 24. SQL filters
screenings before ranking, pages distinct Movie IDs ordered by the earliest
qualifying showtime and ID, then attaches the first three qualifying screenings
total. A single SQL snapshot supplies rows and totals, even beyond the last page.
The injected clock is read once per request. The endpoint is uncached to avoid
serving an old upcoming-screening cutoff. Existing APIs remain available.

Movies uses its own `GET /v1/movies` title search and 24-item pages. Neither browse
mode drains its endpoint or fetches per-poster metadata. Movie navigation resolves
exact metadata and uses the shared schedule loader, including all pages in its
requested window. Detail and cinema completion remain separate slices.

## Environment and provenance

- Baseline: merged PR #339, `4018ee046550920cc4ada3b399aa8ad5c8fda7c4`.
- Implementation revision: the commit containing this report and subsequent
  review fixes linked from the #333 draft PR. No main-checkout changes were used.
- Local Node v26.13.0, pnpm 11.17.0, Python 3.13.14, PostgreSQL 17 in the disposable
  `marquise-333-db` container. No production database was accessed.
- Browser: Playwright Chromium 156.0.8078.4, desktop 1280x900, touch viewport
  390x844. This is browser touch emulation, not a physical phone or Safari check.
- Built app: `VITE_MARQUISE_API_BASE_URL=http://127.0.0.1:18033`, served from Vite's
  built-artifact server at `http://127.0.0.1:14333`. API CORS permits that origin.
- Controlled database: 28 named test movies, 27 eligible today, four screenings
  each across two venues. One catalogue movie has no screenings. Separate gateway
  tests use 27 movies and one with 120 screenings, plus autumn DST boundaries.
- Only the desktop test poster host is intercepted to provide clearly synthetic
  artwork. Mobile image requests deliberately fail. Every `/v1/*` request reaches
  the real HTTP client, FastAPI, application query, read adapter and PostgreSQL.
  Booking links in these controlled rows are test links, never live booking data.

## Checks

| Command, from root unless stated | Result |
| --- | --- |
| `uv run ruff check .` | Pass |
| `uv run ruff format --check .` | Pass |
| `uv run ty check packages/marquise-core/src` | Pass |
| `uv run lint-imports` | Public-facade contract kept |
| `uv run pytest packages/marquise-core/tests/unit_tests --cov=marquise --cov-report=term --cov-fail-under=70 -q` | 773 pass, 82.72% coverage |
| `uv run pytest packages/marquise-core/tests/unit_tests/interface_adapters/readers/test_screening_movie_reader.py -q` | 1 pass, no I/O |
| `uv run pytest apps/marquise-api/tests -q` | 306 pass |
| `uv run pytest apps/marquise-cli/tests -q` | 96 pass |
| `DATABASE_URL=postgresql://postgres:marquise-test@127.0.0.1:55433/marquise_test uv run pytest packages/marquise-core/tests/integration_tests/infrastructure/supabase/gateways/test_screening_movie_reader.py -q` | 2 pass |
| From `web/`: `pnpm lint -- --threads=2` | Pass |
| From `web/`: `pnpm typecheck` | Pass |
| From `web/`: `pnpm test -- --maxWorkers=2` | 64 client, 178 component/demo, 18 interface tests pass |
| From `web/`: `VITE_MARQUISE_API_BASE_URL=http://127.0.0.1:18033 pnpm build` | Pass, emitted CSS check passes |
| From `web/`: `node packages/components/demo/check-isolation.mjs` | Pass across 37 library files |
| `uv run --with playwright python scripts/verify_browse_ui.py` | Pass against the built app and real controlled API/database |
| `git diff --check` | Pass |

The initial browser run used an incorrect expected empty-state sentence. The
actual empty schedule was correct. Updating the assertion to the shared UI's
existing sentence passed. A component booking-link assertion similarly needed
to match the time link separately from its adjacent language acronym.

The Chromium script asserts four/two computed grid columns, white page background,
no horizontal overflow, exact card/preview edge contact, moving into the preview,
three showtimes total, rapid sweeps with one overlay, Escape/focus restoration,
clicking a movie after hover, touch arrow/close, bounded catalogue reads and title
search independent of dates, a catalogue-only movie's schedule, and refresh on a
direct detail link. Initial browsing makes exactly one movie-first request.

Screenshots are written to `/tmp/marquise-333-browser/desktop.png` and `mobile.png`;
request URLs to `requests.json`. Both screenshots were visually inspected. Poster
boxes and title rows align, the nav remains compact, and the white background
extends beyond the content. These images contain test artwork or missing-poster
fallbacks. They are local evidence, not deployment screenshots.

## Reproduce the browser check

Use a fresh disposable PostgreSQL container, never an existing database:

```sh
docker run --name marquise-333-db --rm -d -e POSTGRES_PASSWORD=marquise-test \
  -e POSTGRES_DB=marquise_test -p 127.0.0.1:55433:5432 postgres:17
docker exec -i marquise-333-db psql -U postgres -d marquise_test < scripts/marquise-schema.sql
docker exec -i marquise-333-db psql -U postgres -d marquise_test < web/design/333/seed.sql
DATABASE_URL=postgresql://postgres:marquise-test@127.0.0.1:55433/marquise_test \
  MARQUISE_API_CORS_ORIGINS=http://127.0.0.1:14333 \
  uv run uvicorn marquise_api.app:create_app --factory --host 127.0.0.1 --port 18033
```

In another shell, from `web/`:

```sh
VITE_MARQUISE_API_BASE_URL=http://127.0.0.1:18033 pnpm build
pnpm --filter marquise-interface exec vite preview --host 127.0.0.1 --port 14333 --strictPort
```

Then from root, run the browser command above. Install Playwright's Chromium if
it is absent. The seed creates showtimes one hour ahead. Run before 22:55 Montreal
time so those shows remain in today's window. The deterministic DST/database
unit tests do not have this wall-clock constraint. Stop the two servers and
`docker stop marquise-333-db` when finished.

## Remaining work

#333 intentionally displays only the first batch. #334 owns full movie-detail
completion, #335 listing controls and URLs, #336 append/restoration, #337 real
cinema directory/venue pages, and #338 integrated acceptance across all slices.
The Cinemas route therefore has navigation and its disclosure with an honest
placeholder, without presenting a partial directory as complete.

No live provider, production deployment, physical touch device, or Safari check
was performed. The complete integration suite and final integrated-preview gate
belong to #338. This slice's focused PostgreSQL and Chromium checks passed.
