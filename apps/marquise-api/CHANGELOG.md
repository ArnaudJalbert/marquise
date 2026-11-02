# Changelog

## 2026-11-02

### v0.1.17

- Use the screening write context owned by `WriteScreeningUseCase`. Requires core v0.2.41.

## 2026-11-01

### v0.1.15

- Disable duplicate Uvicorn access logging in the production container and clarify independent public API use, third-party content rights, non-affiliation, and policy links in the API reference. Supports #415.

### v0.1.16

- Make `end` optional on `GET /v1/screening-movies` to list movies with screenings at any future date. Requires core v0.2.35.

### v0.1.14

- Add nullable TMDB rating and vote count to movie and screening-movie responses. Requires core v0.2.33 and migration `373-add-movies-tmdb-score.sql`. Closes #375.

## 2026-10-30

### v0.1.13

- Add repeated cinema and language filters, title search, and Montréal daily-hour bounds to the movie-first screening endpoint. Supports #335.

### v0.1.12

- Add uncached `GET /v1/screening-movies?start=YYYY-MM-DD&end=YYYY-MM-DD&page=1` with fixed 24-movie pages, metadata, and three upcoming previews per movie. Preserve the independent catalogue and screening endpoints. Requires core v0.2.29. Supports #333.

## 2026-10-07

### v0.1.11

- Require `Idempotency-Key` and `X-Change-Reason` for POST, PATCH, and DELETE screening writes. Verified account identity and validated mutations go through the configured audited write use case. Closes #250.
- Replay original success and POST Location, return `409` / `idempotency_conflict` for changed intent, and return retryable `503` with `Retry-After: 1` for write acquisition timeout. Fresh authentication and authorization always precede replay.
- Retry best-effort local cache invalidation on successful replays without repeating data changes or audit records. Document header limits, history, concurrency, credential-free inputs, and schema provisioning. Requires marquise-core v0.2.25 or later.

### v0.1.10

- **Authenticated screening mutations**: Editors and Administrators can create (201 with persisted data and Location), partially edit (200, preserving omitted fields and clearing nullable metadata), and permanently delete (204, with atomic orphan-movie cleanup) screenings. Public reads remain unauthenticated. Closes #257.
- **Validation and errors**: Reject unknown fields, invalid/blank values, naive timestamps, null identity edits, and non-absolute HTTP(S) ticket URLs before executing writes. External-ID collisions use the same `409` / `conflict` code as screening-identity collisions. Framework validation now uses the standard `detail` / `error_code` envelope; rate limiting retains its legacy `error` field alongside that envelope.
- **Throttle before authentication**: Screening writes consume the configured per-IP limit before token verification, including rejected credentials and roles. Exhausted limits return `429` without verification or mutation; successful requests are charged once and retain existing rate-limit and CORS headers.
- **Browser support and freshness**: Configured CORS origins allow bearer-authenticated POST, PATCH, and DELETE. Writes retain per-IP throttling and are uncached. Committed writes invalidate the full instance-local public cache (except empty PATCH); invalidation failures retain success and emit sanitized logs without retry or rollback. Freshness remains best-effort and bounded by cache expiry; other instances are not invalidated.

## 2026-10-04

### v0.1.9

- **Use the screening detail query**: `GET /v1/screenings/{screening_id}` executes the reader-backed `GetScreeningQuery` without constructing domain entities. The HTTP response and missing-screening behavior remain unchanged. Requires marquise-core v0.2.22 or later.

## 2026-09-02

### v0.1.8

- **Prepare Supabase JWT authorization**: reusable FastAPI dependencies call the core token-verification query for authenticated, Editor, and Administrator access. No current endpoint uses them, so all existing routes remain public. Closes #263.

## 2026-08-29

### v0.1.7

- **Use configured screening-list queries**: cinema and movie screening routes execute reader-backed queries directly. Closes #208.
- **Execute configured read use cases directly**: cinema, movie, and screening routes now construct use-case DTOs without pass-through controllers. Closes #188.
- **Cache screening search**: `GET /v1/screenings` responses use a bounded in-memory cache (default 1-hour TTL), with separate fixed-length keys for each query string. Closes #205.

## 2026-08-10

### Deployment

- **CORS**: the deployed API explicitly allows the interface origin.

## 2026-07-29

### v0.1.5

- **Raise default rate limit from 60/min to 3000/min**: accommodates the frontend poster wall fetching many screenings per page load without hitting per-IP throttling.

## 2026-07-19

### v0.1.4

- **Enable CORS for the deployed frontend**: sets `MARQUISE_API_CORS_ORIGINS = "https://marquise-interface.fly.dev"` in `apps/marquise-api/fly.toml`'s `[env]` block so browser requests from the deployed `marquise-interface` site are allowed against the production API (previously only `http://localhost:5173` was allowlisted, via the v0.1.1 change).

## 2026-07-17

### v0.1.3

- **Fix `flyctl deploy` failing on push to `main`**: flyctl resolves `[build].dockerfile` (and the CLI `--dockerfile` flag) relative to the directory containing `fly.toml`, not the repo root. `apps/marquise-api/fly.toml` still had `dockerfile = "apps/marquise-api/Dockerfile"` left over from the pre-move root-`fly.toml` setup, so flyctl looked for `apps/marquise-api/apps/marquise-api/Dockerfile` and failed with "not found". Changed it to `dockerfile = "Dockerfile"` and dropped the now-redundant `--dockerfile` flags from both `deploy-api` and `deploy-interface` jobs in `.github/workflows/fly-deploy.yml` (the interface job's fly.toml already had the correct relative path, but the CLI flag was overriding it with the same broken repo-rooted path).

### v0.1.2

- **Move `fly.toml` into `apps/marquise-api/`**: colocated the Fly config with the Dockerfile it deploys instead of leaving it at the repo root, now that a second Fly app (`marquise-interface`) exists. The Dockerfile still requires repo-root build context (it reaches into `packages/marquise-core` and root `pyproject.toml`/`uv.lock`), so `.github/workflows/fly-deploy.yml` now invokes `flyctl deploy --config apps/marquise-api/fly.toml --dockerfile apps/marquise-api/Dockerfile` from the repo root rather than relying on the implicit root `fly.toml`.
- **`GET /v1/movies` gains bulk-by-ids lookup**: added a repeated `ids` query param (`?ids=a&ids=b`) alongside `?title=` — the two can be combined as an AND filter (movies whose id is in the list *and* whose title matches), or used independently. `ids` is capped at 100 per call (422 via `TooManyMovieIdsError` if exceeded) and additionally capped at the requested page `size` (`ids` count must not exceed `size`; 422 otherwise), and rejects `page != 1` (everything fits on one page by construction). IDs with no matching movie are silently omitted. No separate `/movies/by-ids` route — this reuses the same paginated `Page[MovieResponse]` response shape as the existing list endpoint. When both filters are given, the title match is applied in-memory to the `ids` lookup's results (no second SQL predicate).

## 2026-07-15

### v0.1.1

- **Enable CORS for local frontend dev**: sets `MARQUISE_API_CORS_ORIGINS = "http://localhost:5173"` in root `fly.toml`'s `[env]` block so browser requests from the local Vite dev server (both `marquise-admin` and `marquise-interface`, which default to port 5173) are allowed against the deployed API. `apps/marquise-api/src/marquise_api/app.py` already supported the env var; it was simply never set, so `CORSMiddleware` was never registered and all cross-origin requests were rejected.

### v0.1.0

- **Extract API into a workspace package**: FastAPI application code moved to `apps/marquise-api/` with `Depends(controller)` wiring from `marquise_api.dependencies`. Added `MovieController` and `ScreeningController`. Moved Dockerfile to `apps/marquise-api/`. Closes #105, #106.
