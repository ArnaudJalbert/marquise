"""Marquise — movie showtimes aggregator for Montreal.

Public API
----------
Use :func:`create_factory` or :class:`MarquiseFactory` to obtain
fully-wired controllers::

    from marquise import create_factory

    factory = await create_factory()
    cinemas = await factory.cinema.list()

Alternatively, use the async context manager for automatic cleanup::

    from marquise import MarquiseFactory

    async with MarquiseFactory() as f:
        cinemas = await f.cinema.list()

Everything under ``marquise.domain``, ``marquise.application``,
``marquise.interface_adapters``, and ``marquise.infrastructure`` is
private and must not be imported by external consumers.
"""

from marquise.bootstrap import (
    MarquiseFactory,
    create_factory,
    create_factory_session,
)
from marquise.infrastructure.controllers.auth_controller import AuthController
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.infrastructure.controllers.source_controller import SourceController

__all__ = [
    "AuthController",
    "CinemaController",
    "MarquiseFactory",
    "SourceController",
    "create_factory",
    "create_factory_session",
]
