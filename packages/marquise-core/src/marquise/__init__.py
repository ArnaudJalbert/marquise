"""Marquise movie showtimes aggregator public API.

Open create_factory_session to get a MarquiseFactory and its configured use
cases through this supported facade. Internal package modules are private.
"""

from marquise.application.exceptions import (
    ApplicationError,
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    MetadataFailure,
    MetadataInvalidDataError,
    MetadataNotFoundError,
    MetadataRateLimitedError,
    MetadataUnavailableError,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningNotFoundError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
    TooManyMovieIdsError,
    TooManyScreeningDaysError,
)
from marquise.application.metadata import (
    ProviderIdentity,
)
from marquise.application.movie_workflows import (
    EnrichMovieInputData,
    EnrichMovieOutputData,
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    MovieWorkflowConflictError,
    RefreshMoviesInputData,
    RefreshMoviesOutputData,
)
from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.queries.count_screening_days import CountScreeningDaysQuery
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.queries.get_cinema_source import GetCinemaSourceQuery
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.merge_movies import MergeMoviesUseCase
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.bootstrap import create_factory_session
from marquise.infrastructure.di.factory import MarquiseFactory
from marquise.infrastructure.di.use_case_areas import (
    CinemaUseCases,
    MovieUseCases,
    ScreeningUseCases,
    SourceUseCases,
)

__all__ = [
    "ProviderIdentity",
    "MetadataFailure",
    "MetadataUnavailableError",
    "MetadataRateLimitedError",
    "MetadataNotFoundError",
    "MetadataInvalidDataError",
    "MovieMetadataValues",
    "MovieMetadataSnapshot",
    "EnrichMovieInputData",
    "EnrichMovieOutputData",
    "RefreshMoviesInputData",
    "RefreshMoviesOutputData",
    "MergeMoviesInputData",
    "MergeMoviesOutputData",
    "MovieWorkflowConflictError",
    "RefreshMoviesUseCase",
    "MergeMoviesUseCase",
    "BrowseScreeningMoviesQuery",
    "CountScreeningDaysQuery",
    "ApplicationError",
    "AssignSourceUseCase",
    "CinemaAlreadyExistsError",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "CreateCinemaUseCase",
    "CreateScreeningsCommand",
    "ImportScreeningsCommand",
    "CreateSourceUseCase",
    "DeleteCinemaUseCase",
    "DeleteSourceUseCase",
    "FetchScreeningsFromSourceQuery",
    "GetCinemaMoviesUseCase",
    "GetCinemaScreeningsQuery",
    "GetCinemaSourceQuery",
    "GetCinemaUseCase",
    "GetMovieScreeningsQuery",
    "GetMovieUseCase",
    "GetScreeningQuery",
    "create_factory_session",
    "ListCinemaSourceAssignmentsQuery",
    "ListCinemasUseCase",
    "ListMoviesUseCase",
    "ListRegistrySourcesUseCase",
    "ListSourcesUseCase",
    "MarquiseFactory",
    "CinemaUseCases",
    "MovieUseCases",
    "ScreeningUseCases",
    "SourceUseCases",
    "MovieNotFoundError",
    "ScreeningAlreadyExistsError",
    "ScreeningExternalIdConflictError",
    "ScreeningNotFoundError",
    "SearchScreeningsQuery",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
    "TooManyScreeningDaysError",
    "UnassignSourceUseCase",
    "UpdateCinemaUseCase",
]
