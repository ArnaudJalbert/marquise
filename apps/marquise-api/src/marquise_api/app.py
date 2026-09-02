"""FastAPI application factory for the read-only public API.

Environment variables
---------------------
MARQUISE_API_CACHE_TTL_SECONDS
    In-memory response cache TTL (default: 3600).
MARQUISE_API_CORS_ORIGINS
    Comma-separated list of allowed CORS origins (default: empty — no
    cross-origin requests permitted). Example:
    ``http://localhost:3000,https://myfrontend.example.com``
MARQUISE_API_RATE_LIMIT
    Per-IP request rate limit, in slowapi's ``<count>/<period>`` string
    syntax (default: ``60/minute``). Example: ``120/minute``.
SUPABASE_URL
    Supabase project URL used to discover JWT signing keys for protected routes.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_pagination import add_pagination
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse, Response

from marquise import ApplicationError, MarquiseFactory, create_factory
from marquise_api.auth import (
    SupabaseJwtVerifier,
    SupabaseSigningKeyProvider,
    TokenVerifier,
)
from marquise_api.dependencies import get_factory
from marquise_api.exception_handlers import (
    application_error_handler,
    unhandled_exception_handler,
    value_error_handler,
)
from marquise_api.logging_middleware import (
    RequestLoggingMiddleware,
    configure_logging,
)
from marquise_api.rate_limit import limiter
from marquise_api.routers import (
    cinemas_router,
    movies_router,
    screenings_router,
)

#: Default in-memory response cache TTL, in seconds. The database is only
#: refreshed once a day, so an hour keeps responses fresh while still
#: absorbing the vast majority of repeat traffic between refreshes.
DEFAULT_CACHE_TTL_SECONDS = 3600
#: Namespace prefix for cached responses. Public so tests can clear
#: exactly this app's cache entries between repeated create_app() calls
#: (see tests/unit_tests/infrastructure/api/test_api.py) without reaching
#: into fastapi-cache2's internals.
CACHE_PREFIX = "marquise-api-cache"

#: Default CORS allowed origins (empty = no cross-origin requests permitted).
#: Override via the ``MARQUISE_API_CORS_ORIGINS`` env var as a comma-separated
#: list of origins, e.g. ``http://localhost:3000,https://app.example.com``.
DEFAULT_CORS_ORIGINS: str = ""


def _parse_cors_origins(raw: str | None) -> list[str]:
    """Parse a comma-separated CORS origins string into a list.

    Args:
        raw: The raw env-var value, or ``None``.

    Returns:
        A list of origin strings. Empty strings are filtered out.
    """
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(
    factory: MarquiseFactory | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    Args:
        factory: An optional pre-built factory. When provided (e.g. in
            tests), it is used as-is and its lifecycle is the caller's
            responsibility. When omitted, a ``MarquiseFactory`` is created
            and its database pool is opened on startup and closed on shutdown.
        token_verifier: Optional injected access-token verifier. When omitted,
            Supabase verification is configured from ``SUPABASE_URL`` if set.

    Returns:
        A configured ``FastAPI`` instance.
    """
    configure_logging()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if token_verifier is None and supabase_url:
        issuer = f"{supabase_url}/auth/v1"
        token_verifier = SupabaseJwtVerifier(
            signing_key_provider=SupabaseSigningKeyProvider(
                f"{issuer}/.well-known/jwks.json"
            ),
            issuer=issuer,
        )

    cache_ttl_seconds = int(
        os.environ.get("MARQUISE_API_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)
    )

    FastAPICache.reset()
    FastAPICache.init(InMemoryBackend(), prefix=CACHE_PREFIX, expire=cache_ttl_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if factory is None:
            owned = await create_factory()
            app.state.factory = owned
            try:
                yield
            finally:
                await owned.shutdown()
        else:
            app.state.factory = factory
            yield

    app = FastAPI(
        title="Marquise API",
        description="""
Read-only public access to Montreal cinema showtimes, aggregated across
multiple cinema chains and independent theatres.

## Authentication

Current read endpoints under `/v1`, plus `/health` and `/ready`, are public.
Write endpoints may require a Supabase bearer token carrying a Marquise role.

## Rate limiting

Requests are limited per client IP to **60 requests/minute** by default
(configurable server-side via `MARQUISE_API_RATE_LIMIT`). Exceeding the
limit returns `429 Too Many Requests`. `/health` and `/ready` are exempt
(they're intended for uptime monitors, not API clients).

## Caching

Responses are cached in-memory for **1 hour** by default (configurable via
`MARQUISE_API_CACHE_TTL_SECONDS`). The underlying showtime data itself is
refreshed at most once a day, so cached responses are never meaningfully
stale relative to the source data.

## Errors

Every error response, including unexpected server errors, shares one JSON
envelope:

```json
{"detail": "human-readable message", "error_code": "machine_readable_code"}
```

Prefer matching on `error_code` over parsing `detail`, whose wording may
change without notice. See each endpoint's documented responses below for
the specific `error_code` values it can return.

## CORS

Disabled by default (no cross-origin browser requests are permitted).
Server operators can allow specific origins via `MARQUISE_API_CORS_ORIGINS`.
""",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.state.token_verifier = token_verifier

    # When a factory is injected (e.g. in tests), make it available even if
    # the lifespan startup is not run by the test client.
    if factory is not None:
        app.state.factory = factory

    # Per-IP rate limiting. The limiter itself is a shared singleton (see
    # rate_limit.py) so that router-level `@limiter.limit(...)` decorators,
    # applied at import time, share its in-memory counters. Reset here so
    # repeated create_app() calls (e.g. across tests) start from a clean
    # slate. Registered before CORSMiddleware below so that CORS ends up as
    # the outermost middleware (Starlette applies the last-registered
    # middleware first) — otherwise 429 responses would be returned before
    # CORS headers are attached, breaking browser clients.
    async def _rate_limit_adapter(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RateLimitExceeded)
        return _rate_limit_exceeded_handler(request, exc)

    limiter.reset()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_adapter)
    app.add_middleware(SlowAPIMiddleware)

    # Global error-to-response mapping, in one place instead of per-router
    # try/except (see exception_handlers.py for the status/error_code table).
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # CORS — restrictive by default (no origins allowed). Override via the
    # MARQUISE_API_CORS_ORIGINS env var as a comma-separated list.
    cors_origins = _parse_cors_origins(
        os.environ.get("MARQUISE_API_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    )
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    # Structured request logging — registered last (outermost) so it wraps
    # the entire stack above (CORS, rate limiting, routing) and its logged
    # duration reflects true end-to-end request time.
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health", tags=["meta"])
    @limiter.exempt
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    @app.get(
        "/ready",
        tags=["meta"],
        responses={
            503: {
                "description": "The database pool cannot currently serve queries.",
                "content": {"application/json": {"example": {"status": "unavailable"}}},
            }
        },
    )
    @limiter.exempt
    async def ready(factory: MarquiseFactory = Depends(get_factory)) -> JSONResponse:
        """Readiness probe — verifies the database pool can serve queries."""
        if await factory.check_database_health():
            return JSONResponse({"status": "ok"}, status_code=200)
        return JSONResponse({"status": "unavailable"}, status_code=503)

    v1_router = APIRouter(prefix="/v1")
    v1_router.include_router(cinemas_router)
    v1_router.include_router(movies_router)
    v1_router.include_router(screenings_router)
    app.include_router(v1_router)

    add_pagination(app)

    return app
