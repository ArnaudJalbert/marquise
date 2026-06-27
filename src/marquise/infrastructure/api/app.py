"""FastAPI application factory for the read-only public API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from marquise.infrastructure.api.routers import cinemas_router, movies_router
from marquise.infrastructure.di.container import Container


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

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    app.include_router(cinemas_router)
    app.include_router(movies_router)

    return app
