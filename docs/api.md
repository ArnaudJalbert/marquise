# Read-Only REST API

Marquise ships a read-only FastAPI with pagination, in-memory caching, and configurable CORS.

## Starting the API

```bash
make api
```

By default the server listens on `http://localhost:8000`. OpenAPI docs are at
`/docs` and a liveness probe at `/health`.

## Production

A production instance is deployed to Fly.io and publicly reachable at
`https://marquise-api.fly.dev`. Hosted OpenAPI docs are at
[https://marquise-api.fly.dev/docs](https://marquise-api.fly.dev/docs).

## Endpoints

All routes except `/health` are versioned under a `/v1` prefix, so that
breaking changes (pagination, response shape, etc.) can ship as `/v2` without
disrupting existing consumers.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `GET` | `/v1/cinemas` | List cinemas, optionally filtered by `?name=` |
| `GET` | `/v1/cinemas/{id}/screenings` | List all of a cinema's screenings (no filters beyond pagination — see below) |
| `GET` | `/v1/cinemas/{id}/movies` | List distinct movies currently screening at a cinema (`?from=&to=`) |
| `GET` | `/v1/movies` | List movies, optionally filtered by `?title=` |
| `GET` | `/v1/movies/{id}` | Retrieve a single movie by its ID |
| `GET` | `/v1/movies/{id}/screenings` | List all of a movie's screenings (no filters beyond pagination — see below) |
| `GET` | `/v1/screenings` | Search screenings across all cinemas (`?movie=&movie_id=&cinema_id=&from=&to=&language=`) |
| `GET` | `/v1/screenings/{id}` | Retrieve a single screening by its ID |

`GET /v1/cinemas/{id}/screenings` and `GET /v1/movies/{id}/screenings` are
deliberately unfiltered beyond their path-scoped ID (only `page`/`size` are
accepted) — use `GET /v1/screenings` for date range, cross-entity, or
language filtering.

### Pagination

List endpoints use `page`/`size` query parameters (from fastapi-pagination):

```bash
# Page 2, 10 items per page
curl "http://localhost:8000/v1/cinemas?page=2&size=10"

# Response includes: items[], total, page, size, pages
```

Default: `page=1`, `size=50`. Maximum `size` is 100.

### Date ranges

`GET /v1/cinemas/{id}/movies` and `GET /v1/screenings` accept `from` and `to`
query parameters in ISO-8601 format:

```bash
curl "http://localhost:8000/v1/screenings?cinema_id=cin-1&from=2026-07-09&to=2026-07-16"
```

`GET /v1/cinemas/{id}/movies` defaults to `from` = start of today (UTC),
`to` = `from` + 7 days when omitted. `GET /v1/screenings` is unbounded when
`from`/`to` are omitted — it searches the full screenings dataset.

## Caching

Responses are cached in-memory via fastapi-cache2. The first request for a given
combination of endpoint + query parameters is a cache miss; subsequent identical
requests hit the cache until the TTL expires.

Configure the TTL:

```bash
export MARQUISE_API_CACHE_TTL_SECONDS=3600   # 1 hour (default)
```

`GET /health` is intentionally never cached.

## Rate Limiting

The API applies a per-IP request rate limit via [slowapi](https://pypi.org/project/slowapi/),
backed by the same in-memory approach as the response cache — no external
store (e.g. Redis) required.

Default: **60 requests per minute per client IP**. Requests over the limit
receive a `429` response:

```json
{"error": "Rate limit exceeded: 60 per 1 minute"}
```

along with these headers:

- `X-RateLimit-Limit` — the configured limit
- `X-RateLimit-Remaining` — requests left in the current window
- `X-RateLimit-Reset` — Unix timestamp when the window resets
- `Retry-After` — seconds to wait before retrying

`GET /health` is exempt from rate limiting.

Configure the limit with the `MARQUISE_API_RATE_LIMIT` env var, using
[slowapi's](https://limits.readthedocs.io/en/stable/quickstart.html#rate-limit-string-notation)
`<count>/<second|minute|hour|day>` string syntax:

```bash
export MARQUISE_API_RATE_LIMIT="120/minute"
```

## CORS

The API is **CORS-restrictive by default**: no cross-origin requests are
permitted. Browser-based clients (e.g. a JavaScript frontend) will be blocked
unless you configure allowed origins.

### Configuring CORS

Set the `MARQUISE_API_CORS_ORIGINS` environment variable to a comma-separated
list of origins:

```bash
# Single origin
export MARQUISE_API_CORS_ORIGINS="http://localhost:3000"

# Multiple origins
export MARQUISE_API_CORS_ORIGINS="http://localhost:3000,https://myapp.example.com"
```

When the env var is set, the API responds with appropriate CORS headers:

- `Access-Control-Allow-Origin` — echoes the requesting origin (if allowed)
- `Access-Control-Allow-Methods: GET` — the API is read-only
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Headers: *`

### How it works

The middleware is registered in `create_app()` in
`apps/marquise-api/src/marquise_api/app.py`. It reads the env var, parses it via
the `_parse_cors_origins()` helper, and only adds `CORSMiddleware` when at least
one origin is configured — so there is zero overhead when CORS is not needed.

### Preflight requests

The API handles `OPTIONS` preflight requests automatically when CORS origins
are configured. No additional setup is required.

## How the code is organized

```
apps/marquise-api/src/marquise_api/
├── app.py              # create_app() factory, lifespan, CORS, caching, rate limiting
├── dependencies.py     # get_cinema_controller() / get_movie_controller() / get_screening_controller()
├── rate_limit.py       # Shared slowapi Limiter used by app.py and the routers
├── schemas/            # Pydantic response models
└── routers/
    ├── __init__.py     # Re-exports router modules
    ├── _dependencies.py # Shared resolve_showtimes_date_range dependency
    ├── cinemas.py      # GET /cinemas, GET /cinemas/{id}/screenings, GET /cinemas/{id}/movies
    ├── movies.py       # GET /movies, GET /movies/{id}, GET /movies/{id}/screenings
    └── screenings.py   # GET /screenings, GET /screenings/{id}
```

Routers themselves are unprefixed; `create_app()` wraps them in an
`APIRouter(prefix="/v1")` before mounting them on the app, so the `/v1`
boundary lives in one place.

All routes delegate to application-layer use cases via the DI container. There
is no business logic or data access in the routers.
