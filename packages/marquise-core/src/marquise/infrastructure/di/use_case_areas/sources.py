"""Wired source and cinema-source assignment use cases and queries."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from marquise.application.queries.get_cinema_source import GetCinemaSourceQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.list_sources import ListSourcesQuery
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.infrastructure.di.queries import (
    build_get_cinema_source_query,
    build_list_cinema_source_assignments_query,
    build_list_sources_query,
)
from marquise.infrastructure.di.source_management import (
    build_assign_source_use_case,
    build_create_source_use_case,
    build_delete_source_use_case,
    build_unassign_source_use_case,
)
from marquise.infrastructure.di.use_case_areas.cinemas import build_cinema_repository
from marquise.infrastructure.postgres.config.settings import Settings
from marquise.interface_adapters.repositories.source_registry import SourceRegistry


@dataclass(frozen=True, slots=True)
class SourceUseCases:
    """Wired use cases and queries that manage sources and their assignments."""

    list_registry_sources_use_case: ListRegistrySourcesUseCase
    create_source_use_case: CreateSourceUseCase
    list_sources_query: ListSourcesQuery
    delete_source_use_case: DeleteSourceUseCase
    assign_source_use_case: AssignSourceUseCase
    unassign_source_use_case: UnassignSourceUseCase
    get_cinema_source_query: GetCinemaSourceQuery
    list_cinema_source_assignments_query: ListCinemaSourceAssignmentsQuery


def build_source_use_cases(
    pool: asyncpg.Pool, settings: Settings, source_registry: SourceRegistry
) -> SourceUseCases:
    """Wire every source and cinema-source assignment use case and query.

    Args:
        pool: Open connection pool shared by every gateway.
        settings: Settings that name the database schema.
        source_registry: Registry whose sources the listing reports.

    Returns:
        The source use cases.
    """
    schema = settings.schema
    return SourceUseCases(
        list_registry_sources_use_case=ListRegistrySourcesUseCase(
            registry=source_registry
        ),
        create_source_use_case=build_create_source_use_case(pool, schema),
        list_sources_query=build_list_sources_query(pool, schema),
        delete_source_use_case=build_delete_source_use_case(pool, schema),
        assign_source_use_case=build_assign_source_use_case(
            pool, schema, build_cinema_repository(pool, schema)
        ),
        unassign_source_use_case=build_unassign_source_use_case(pool, schema),
        get_cinema_source_query=build_get_cinema_source_query(pool, schema),
        list_cinema_source_assignments_query=(
            build_list_cinema_source_assignments_query(pool, schema)
        ),
    )
