"""Repository interface re-exports."""

from marquise.application.repositories.cinema_repository import CinemaRepository
from marquise.application.repositories.cinema_source_assignment_repository import (
    CinemaSourceAssignmentRepository,
)
from marquise.application.repositories.movie_repository import MovieRepository
from marquise.application.repositories.screening_repository import (
    ScreeningRepository,
)
from marquise.application.repositories.source_definition_repository import (
    SourceDefinitionRepository,
)
from marquise.application.repositories.source_registry_query import (
    RegistrySourceEntry,
    ShowtimeRow,
    SourceRegistryQuery,
)

__all__ = [
    "CinemaRepository",
    "CinemaSourceAssignmentRepository",
    "MovieRepository",
    "RegistrySourceEntry",
    "ScreeningRepository",
    "ShowtimeRow",
    "SourceDefinitionRepository",
    "SourceRegistryQuery",
]
