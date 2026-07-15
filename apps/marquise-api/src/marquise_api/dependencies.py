"""Shared FastAPI dependencies for the read-only API.

Provides per-controller dependency injection functions that resolve
controllers from the :class:`~marquise.MarquiseFactory` stored on
``app.state``.
"""

from __future__ import annotations

from fastapi import Request

from marquise import (
    CinemaController,
    MarquiseFactory,
    MovieController,
    ScreeningController,
)


def get_factory(request: Request) -> MarquiseFactory:
    """Return the MarionFactory stored on the application state.

    Args:
        request: The incoming request (carries the app instance).

    Returns:
        The ``MarquiseFactory`` initialized during application startup.
    """
    return request.app.state.factory


def get_cinema_controller(request: Request) -> CinemaController:
    """Return the cinema controller from the application state.

    Args:
        request: The incoming request (carries the app instance).

    Returns:
        The ``CinemaController`` managed by the factory.
    """
    return request.app.state.factory.cinema


def get_movie_controller(request: Request) -> MovieController:
    """Return the movie controller from the application state.

    Args:
        request: The incoming request (carries the app instance).

    Returns:
        The ``MovieController`` managed by the factory.
    """
    return request.app.state.factory.movie


def get_screening_controller(request: Request) -> ScreeningController:
    """Return the screening controller from the application state.

    Args:
        request: The incoming request (carries the app instance).

    Returns:
        The ``ScreeningController`` managed by the factory.
    """
    return request.app.state.factory.screening
