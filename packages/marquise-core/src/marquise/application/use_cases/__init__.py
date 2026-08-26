"""Application use cases for Marquise."""

from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import (
    CreateScreeningsCommand,
    ImportedScreeningData,
)
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
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

__all__ = [
    "AssignSourceUseCase",
    "CreateCinemaUseCase",
    "CreateMissingMoviesCommand",
    "CreateScreeningsCommand",
    "CreateSourceUseCase",
    "DeleteCinemaUseCase",
    "DeleteSourceUseCase",
    "FetchScreeningsFromSourceQuery",
    "GetCinemaUseCase",
    "GetCinemaSourceUseCase",
    "ImportedScreeningData",
    "ListCinemaSourceAssignmentsQuery",
    "ListCinemasUseCase",
    "ListRegistrySourcesUseCase",
    "ListSourcesUseCase",
    "UnassignSourceUseCase",
    "UpdateCinemaUseCase",
]
