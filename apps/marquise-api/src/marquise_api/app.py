"""FastAPI application factory for public catalog reads.

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
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_pagination import add_pagination
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response

from marquise import ApplicationError, MarquiseFactory, create_factory
from marquise_api.dependencies import get_factory
from marquise_api.exception_handlers import (
    application_error_handler,
    http_exception_handler,
    request_validation_error_handler,
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
    screening_movies_router,
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


def _create_lifespan(
    factory: MarquiseFactory | None,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = await _set_factory(app, factory)
        try:
            yield
        finally:
            if owned is not None:
                await owned.shutdown()

    return lifespan


async def _set_factory(
    app: FastAPI, factory: MarquiseFactory | None
) -> MarquiseFactory | None:
    if factory is not None:
        app.state.factory = factory
        return None
    owned = await create_factory()
    app.state.factory = owned
    return owned


def _initialize_cache() -> None:
    cache_ttl_seconds = int(
        os.environ.get("MARQUISE_API_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)
    )
    FastAPICache.reset()
    FastAPICache.init(InMemoryBackend(), prefix=CACHE_PREFIX, expire=cache_ttl_seconds)


def _configure_state(app: FastAPI, factory: MarquiseFactory | None) -> None:
    if factory is not None:
        app.state.factory = factory


def _configure_rate_limiting(app: FastAPI) -> None:
    limiter.reset()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_adapter)
    app.add_middleware(SlowAPIMiddleware)


async def _rate_limit_adapter(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RateLimitExceeded)
    response = _rate_limit_exceeded_handler(request, exc)
    return JSONResponse(
        _rate_limit_body(request, exc),
        status_code=429,
        headers=_rate_limit_headers(response),
    )


def _rate_limit_body(request: Request, exc: RateLimitExceeded) -> dict[str, str | None]:
    message = f"Rate limit exceeded: {exc.detail}"
    return {
        "error": message,
        "detail": message,
        "error_code": "rate_limit_exceeded",
        "request_id": getattr(request.state, "request_id", None),
    }


def _rate_limit_headers(response: Response) -> dict[str, str]:
    return {
        key: value for key, value in response.headers.items() if key != "content-length"
    }


def _configure_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def _configure_cors(app: FastAPI) -> None:
    origins = _configured_cors_origins()
    if origins:
        _add_cors_middleware(app, origins)


def _configured_cors_origins() -> list[str]:
    return _parse_cors_origins(
        os.environ.get("MARQUISE_API_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    )


def _add_cors_middleware(app: FastAPI, origins: list[str]) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


def _configure_middleware(app: FastAPI) -> None:
    # Add rate limiting before CORS so CORS wraps its 429 responses.
    _configure_rate_limiting(app)
    _configure_exception_handlers(app)
    _configure_cors(app)


def _configure_routes(app: FastAPI) -> None:
    _configure_probe_routes(app)
    _configure_api_routes(app)


def _configure_probe_routes(app: FastAPI) -> None:
    _configure_health_route(app)
    _configure_readiness_route(app)


@limiter.exempt
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@limiter.exempt
async def ready(factory: MarquiseFactory = Depends(get_factory)) -> JSONResponse:
    """Readiness probe. Verifies the database pool can serve queries."""
    return _readiness_response(await factory.check_database_health())


def _readiness_response(is_healthy: bool) -> JSONResponse:
    if is_healthy:
        return JSONResponse({"status": "ok"}, status_code=200)
    return JSONResponse({"status": "unavailable"}, status_code=503)


def _configure_health_route(app: FastAPI) -> None:
    app.add_api_route("/health", health, methods=["GET"], tags=["meta"])


def _configure_readiness_route(app: FastAPI) -> None:
    app.add_api_route(
        "/ready",
        ready,
        methods=["GET"],
        tags=["meta"],
        responses={
            503: {
                "description": "The database pool cannot currently serve queries.",
                "content": {"application/json": {"example": {"status": "unavailable"}}},
            }
        },
    )


def _configure_api_routes(app: FastAPI) -> None:
    v1_router = APIRouter(prefix="/v1")
    v1_router.include_router(cinemas_router)
    v1_router.include_router(movies_router)
    v1_router.include_router(screenings_router)
    v1_router.include_router(screening_movies_router)
    app.include_router(v1_router)


def create_app(factory: MarquiseFactory | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        factory: An optional pre-built factory. When provided, it is used as-is
            and its lifecycle is the caller's responsibility. When omitted, a
            configured MarquiseFactory is created and managed by the app.

    Returns:
        A configured FastAPI instance.
    """
    configure_logging()
    _initialize_cache()
    app = FastAPI(
        title="Marquise API",
        description="""
Public read access to Montreal showtimes across multiple cinema chains and
independent theatres.

## Public reuse and source rights

The public API is intended for independent applications as well as Marquise.
Access does not grant a license to third-party film data, descriptions, or images.
Check the applicable source terms and attribution requirements before reusing
content. Marquise does not grant a blanket open-data license to API responses.
Code licensing and third-party content rights are separate.

See [Terms of use](https://marquise.mov/terms),
[source credits](https://marquise.mov/about), and
[Privacy](https://marquise.mov/privacy).
Marquise is an independent personal project, not officially affiliated with
Cineplex, TMDB, or the referenced cinemas, ticket providers, or source websites.

## Access

Every endpoint under ``/v1``, including queries sent with POST, plus ``/health``
and ``/ready``, is public and read-only. No endpoint takes credentials.

## Rate limiting

Requests are limited per client IP to **3000 requests/minute** by default
(configurable server-side via `MARQUISE_API_RATE_LIMIT`). Exceeding the
limit returns `429 Too Many Requests`. `/health` and `/ready` are exempt
(they're intended for uptime monitors, not API clients).

## Caching

Public read responses are cached in-memory for **1 hour** by default
(configurable via `MARQUISE_API_CACHE_TTL_SECONDS`).

## Errors

Every error response, including unexpected server errors, shares one JSON
envelope:

```json
{"detail": "human-readable message", "error_code": "machine_readable_code"}
```

Prefer matching on `error_code` over parsing `detail`, whose wording may
change without notice. See each endpoint's documented responses below for
the specific `error_code` values it can return. Missing resources use
`not_found` (404); invalid requests use `invalid_input` (422); rate-limit errors
use `rate_limit_exceeded` (429) and also retain the legacy `error` field.

## CORS

Disabled by default (no cross-origin browser requests are permitted).
Server operators can allow specific origins via `MARQUISE_API_CORS_ORIGINS`.
Configured origins support GET and POST.
""",
        version="1.0.0",
        lifespan=_create_lifespan(factory),
    )
    _configure_state(app, factory)
    _configure_middleware(app)
    # Registered last so request logging wraps the complete middleware stack.
    app.add_middleware(RequestLoggingMiddleware)
    _configure_routes(app)
    add_pagination(app)

    return app
