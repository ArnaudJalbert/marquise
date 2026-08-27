"""Marquise movie showtimes aggregator public API.

Use :func:`create_factory` or :class:`MarquiseFactory` to obtain configured
use cases through this supported facade. Internal package modules are private.
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
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_screenings import (
    GetCinemaScreeningsUseCase,
)
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.get_movie_screenings import (
    GetMovieScreeningsUseCase,
)
from marquise.application.use_cases.get_screening import GetScreeningUseCase
from marquise.application.use_cases.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.search_screenings import SearchScreeningsQuery
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.bootstrap import (
    MarquiseFactory,
    create_factory,
    create_factory_session,
)

__all__ = [
    "ApplicationError",
    "AssignSourceUseCase",
    "CinemaAlreadyExistsError",
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
    "GetCinemaMoviesUseCase",
    "GetCinemaScreeningsUseCase",
    "GetCinemaSourceUseCase",
    "GetCinemaUseCase",
    "GetMovieScreeningsUseCase",
    "GetMovieUseCase",
    "GetScreeningUseCase",
    "create_factory",
    "create_factory_session",
    "ListCinemaSourceAssignmentsQuery",
    "ListCinemasUseCase",
    "ListMoviesUseCase",
    "ListRegistrySourcesUseCase",
    "ListSourcesUseCase",
    "MarquiseFactory",
    "MovieNotFoundError",
    "ScreeningAlreadyExistsError",
    "ScreeningNotFoundError",
    "SearchScreeningsQuery",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
    "UnassignSourceUseCase",
    "UpdateCinemaUseCase",
]
