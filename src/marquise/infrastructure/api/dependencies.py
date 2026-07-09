"""Shared FastAPI dependencies for the read-only API."""

from __future__ import annotations

from fastapi import Request

from marquise.infrastructure.di.container import Container


def get_container(request: Request) -> Container:
    """Return the DI container stored on the application state.

    Args:
        request: The incoming request (carries the app instance).

    Returns:
        The ``Container`` initialized during application startup.
    """
    return request.app.state.container
