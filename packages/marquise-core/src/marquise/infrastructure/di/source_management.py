"""Source-definition and cinema-assignment dependency wiring."""

from __future__ import annotations

import asyncpg

from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.infrastructure.supabase.gateways.cinema_source_assignment import (
    SupabaseCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.supabase.gateways.source_definition import (
    SupabaseSourceDefinitionGateway,
)
from marquise.interface_adapters.readers.cinema_source_assignment_reader import (
    SupabaseCinemaSourceAssignmentReader,
)
from marquise.interface_adapters.repositories.supabase.cinema_source_assignment_repository import (  # noqa: E501
    SupabaseCinemaSourceAssignmentRepository,
)
from marquise.interface_adapters.repositories.supabase.source_definition_repository import (  # noqa: E501
    SupabaseSourceDefinitionRepository,
)


def _source_repository(
    pool: asyncpg.Pool, schema: str
) -> SupabaseSourceDefinitionRepository:
    return SupabaseSourceDefinitionRepository(
        gateway=SupabaseSourceDefinitionGateway(pool=pool, schema=schema)
    )


def _assignment_repository(
    pool: asyncpg.Pool, schema: str
) -> SupabaseCinemaSourceAssignmentRepository:
    return SupabaseCinemaSourceAssignmentRepository(
        gateway=SupabaseCinemaSourceAssignmentGateway(pool=pool, schema=schema)
    )


def build_create_source_use_case(
    pool: asyncpg.Pool, schema: str
) -> CreateSourceUseCase:
    """Build source-creation use case."""
    return CreateSourceUseCase(source_repository=_source_repository(pool, schema))


def build_list_sources_use_case(pool: asyncpg.Pool, schema: str) -> ListSourcesUseCase:
    """Build source-listing use case."""
    return ListSourcesUseCase(source_repository=_source_repository(pool, schema))


def build_delete_source_use_case(
    pool: asyncpg.Pool, schema: str
) -> DeleteSourceUseCase:
    """Build source-deletion use case."""
    return DeleteSourceUseCase(source_repository=_source_repository(pool, schema))


def build_assign_source_use_case(
    pool: asyncpg.Pool,
    schema: str,
    cinema_repository: CinemaRepository,
) -> AssignSourceUseCase:
    """Build cinema-source assignment use case."""
    return AssignSourceUseCase(
        cinema_repository=cinema_repository,
        source_definition_repository=_source_repository(pool, schema),
        assignment_repository=_assignment_repository(pool, schema),
    )


def build_unassign_source_use_case(
    pool: asyncpg.Pool, schema: str
) -> UnassignSourceUseCase:
    """Build cinema-source unassignment use case."""
    return UnassignSourceUseCase(
        assignment_repository=_assignment_repository(pool, schema)
    )


def build_get_cinema_source_use_case(
    pool: asyncpg.Pool, schema: str
) -> GetCinemaSourceUseCase:
    """Build cinema-source lookup use case."""
    return GetCinemaSourceUseCase(
        assignment_repository=_assignment_repository(pool, schema)
    )


def build_list_cinema_source_assignments_query(
    pool: asyncpg.Pool, schema: str
) -> ListCinemaSourceAssignmentsQuery:
    """Build cinema-source assignment listing query."""
    return ListCinemaSourceAssignmentsQuery(
        reader=SupabaseCinemaSourceAssignmentReader(pool=pool, schema=schema)
    )
