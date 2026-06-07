"""Repository interface re-exports."""

from marquise.application.repositories.cinema_repository import CinemaRepository
from marquise.application.repositories.cinema_source_assignment_repository import (
    CinemaSourceAssignmentRepository,
)
from marquise.application.repositories.source_definition_repository import (
    SourceDefinitionRepository,
)
from marquise.application.repositories.source_registry_query import (
    RegistrySourceEntry,
    SourceRegistryQuery,
)

__all__ = [
    "CinemaRepository",
    "CinemaSourceAssignmentRepository",
    "RegistrySourceEntry",
    "SourceDefinitionRepository",
    "SourceRegistryQuery",
]
