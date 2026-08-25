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
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.bootstrap import (
    MarquiseFactory,
    create_factory,
    create_factory_session,
)
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.infrastructure.controllers.movie_controller import MovieController
from marquise.infrastructure.controllers.screening_controller import ScreeningController

__all__ = [
    "ApplicationError",
    "AssignSourceUseCase",
    "CinemaAlreadyExistsError",
    "CinemaController",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "CreateCinemaUseCase",
    "CreateMissingMoviesCommand",
    "CreateScreeningsCommand",
    "CreateSourceUseCase",
    "DeleteCinemaUseCase",
    "DeleteSourceUseCase",
    "FetchScreeningsFromSourceQuery",
    "GetCinemaSourceUseCase",
    "create_factory",
    "create_factory_session",
    "ListCinemaSourceAssignmentsQuery",
    "ListCinemasUseCase",
    "ListRegistrySourcesUseCase",
    "ListSourcesUseCase",
    "MarquiseFactory",
    "MovieController",
    "MovieNotFoundError",
    "ScreeningAlreadyExistsError",
    "ScreeningController",
    "ScreeningNotFoundError",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
    "UnassignSourceUseCase",
    "UpdateCinemaUseCase",
]
