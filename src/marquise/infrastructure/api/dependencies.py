"""Shared FastAPI dependencies for the read-only API."""

from __future__ import annotations

from fastapi import Request

from marquise.infrastructure.api.cache import TTLCache
from marquise.infrastructure.di.container import Container


def get_container(request: Request) -> Container:
    """Return the DI container stored on the application state.

    Args:
        request: The incoming request (carries the app instance).

    Returns:
        The ``Container`` initialized during application startup.
    """
    return request.app.state.container


def get_cache(request: Request) -> TTLCache:
    """Return the response cache stored on the application state.

    Args:
        request: The incoming request (carries the app instance).

    Returns:
        The ``TTLCache`` initialized during application startup.
    """
    return request.app.state.cache
