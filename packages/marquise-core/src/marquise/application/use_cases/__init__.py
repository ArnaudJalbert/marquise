"""Application use cases for Marquise."""

from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_movies import CreateMoviesCommand
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
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
    "CreateMoviesCommand",
    "CreateScreeningsCommand",
    "CreateSourceUseCase",
    "DeleteCinemaUseCase",
    "DeleteSourceUseCase",
    "GetCinemaUseCase",
    "GetCinemaSourceUseCase",
    "ImportScreeningsCommand",
    "ListCinemasUseCase",
    "ListRegistrySourcesUseCase",
    "ListSourcesUseCase",
    "UnassignSourceUseCase",
    "UpdateCinemaUseCase",
]
