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

from marquise.application.exceptions import (
    ApplicationError,
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
    ScreeningNotFoundError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
    TooManyMovieIdsError,
)
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.bootstrap import (
    MarquiseFactory,
    create_factory,
    create_factory_session,
)
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.infrastructure.controllers.movie_controller import MovieController
from marquise.infrastructure.controllers.screening_controller import ScreeningController
from marquise.infrastructure.controllers.source_controller import SourceController

__all__ = [
    "ApplicationError",
    "CinemaAlreadyExistsError",
    "CinemaController",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "CreateCinemaUseCase",
    "DeleteCinemaUseCase",
    "create_factory",
    "create_factory_session",
    "ListCinemasUseCase",
    "MarquiseFactory",
    "MovieController",
    "MovieNotFoundError",
    "ScreeningAlreadyExistsError",
    "ScreeningController",
    "ScreeningNotFoundError",
    "SourceAlreadyExistsError",
    "SourceController",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
    "UpdateCinemaUseCase",
]
