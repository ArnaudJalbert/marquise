"""Marquise movie showtimes aggregator public API.

Use :func:`create_factory` or :class:`MarquiseFactory` to obtain configured
use cases through this supported facade. Internal package modules are private.
"""

from marquise.application.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    ApplicationError,
    AuthAdministrationError,
    AuthenticationError,
    AuthenticationServiceUnavailableError,
    AuthorizationError,
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    MovieIdentityConflictError,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningNotFoundError,
    SelfDemotionError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
    TooManyMovieIdsError,
)
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.queries.verify_access_token import VerifyAccessTokenQuery
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.auth import (
    AuthenticateAdministratorUseCase,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
)
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.application.use_cases.write_screening import (
    ScreeningIdempotencyConflictError,
    ScreeningWriteBusyError,
    ScreeningWriteContext,
    WriteScreeningUseCase,
)
from marquise.bootstrap import (
    MarquiseFactory,
    create_factory,
    create_factory_session,
)

__all__ = [
    "AccountAlreadyExistsError",
    "ApplicationError",
    "AssignSourceUseCase",
    "AuthenticateAdministratorUseCase",
    "AuthAdministrationError",
    "AuthenticationError",
    "AuthenticationServiceUnavailableError",
    "AuthorizationError",
    "AccountNotFoundError",
    "CinemaAlreadyExistsError",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "CreateCinemaUseCase",
    "CreateMissingMoviesCommand",
    "CreateScreeningUseCase",
    "CreateScreeningsCommand",
    "ImportScreeningsCommand",
    "InviteAccountUseCase",
    "CreateSourceUseCase",
    "DeleteCinemaUseCase",
    "DeleteScreeningUseCase",
    "DeleteSourceUseCase",
    "FetchScreeningsFromSourceQuery",
    "GetCinemaMoviesUseCase",
    "GetCinemaScreeningsQuery",
    "GetCinemaSourceUseCase",
    "GetCinemaUseCase",
    "GetMovieScreeningsQuery",
    "GetMovieUseCase",
    "GetScreeningQuery",
    "create_factory",
    "create_factory_session",
    "ListCinemaSourceAssignmentsQuery",
    "ListCinemasUseCase",
    "ListMoviesUseCase",
    "ListRegistrySourcesUseCase",
    "ListSourcesUseCase",
    "MarquiseFactory",
    "MovieIdentityConflictError",
    "MovieNotFoundError",
    "UpdateScreeningUseCase",
    "ScreeningAlreadyExistsError",
    "ScreeningExternalIdConflictError",
    "ScreeningNotFoundError",
    "SelfDemotionError",
    "SetAccountRoleUseCase",
    "SearchScreeningsQuery",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
    "UnassignSourceUseCase",
    "UpdateCinemaUseCase",
    "VerifyAccessTokenQuery",
    "ScreeningIdempotencyConflictError",
    "ScreeningWriteBusyError",
    "ScreeningWriteContext",
    "WriteScreeningUseCase",
]
