"""FastAPI application factory for the read-only public API.

Environment variables
---------------------
MARQUISE_API_CACHE_TTL_SECONDS
    In-memory response cache TTL (default: 3600).
MARQUISE_API_CORS_ORIGINS
    Comma-separated list of allowed CORS origins (default: empty — no
    cross-origin requests permitted). Example:
    ``http://localhost:3000,https://myfrontend.example.com``
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_pagination import add_pagination

from marquise.infrastructure.api.routers import cinemas_router, movies_router
from marquise.infrastructure.di.container import Container

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


def create_app(container: Container | None = None) -> FastAPI:
    """Build the read-only FastAPI application.

    Args:
        container: An optional pre-built DI container. When provided (e.g. in
            tests), it is used as-is and its lifecycle is the caller's
            responsibility. When omitted, a ``Container`` is created and its
            database pool is opened on startup and closed on shutdown.

    Returns:
        A configured ``FastAPI`` instance.
    """
    cache_ttl_seconds = int(
        os.environ.get("MARQUISE_API_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)
    )

    FastAPICache.reset()
    FastAPICache.init(InMemoryBackend(), prefix=CACHE_PREFIX, expire=cache_ttl_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if container is None:
            owned = Container()
            await owned.initialize()
            app.state.container = owned
            try:
                yield
            finally:
                await owned.shutdown()
        else:
            app.state.container = container
            yield

    app = FastAPI(
        title="Marquise API",
        description="Read-only public access to Montreal cinema showtimes.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # When a container is injected (e.g. in tests), make it available even if
    # the lifespan startup is not run by the test client.
    if container is not None:
        app.state.container = container

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

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    app.include_router(cinemas_router)
    app.include_router(movies_router)

    add_pagination(app)

    return app
