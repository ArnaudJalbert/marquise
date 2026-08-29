"""Read-query dependency wiring."""

from __future__ import annotations

import asyncpg

from marquise.application.queries.get_cinema_screenings import GetCinemaScreeningsQuery
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.screening_data_operations import (
    ReconcileScreeningsCommand,
    ScreeningDataAuditQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import SupabaseScreeningGateway
from marquise.interface_adapters.readers.cinema_source_assignment_reader import (
    SupabaseCinemaSourceAssignmentReader,
)
from marquise.interface_adapters.readers.screening_reader import SupabaseScreeningReader
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


def build_get_cinema_screenings_query(
    pool: asyncpg.Pool, schema: str
) -> GetCinemaScreeningsQuery:
    """Build cinema-screening query."""
    return GetCinemaScreeningsQuery(
        cinema_repository=SupabaseCinemaRepository(
            gateway=SupabaseCinemaGateway(pool=pool, schema=schema)
        ),
        screening_reader=SupabaseScreeningReader(pool=pool, schema=schema),
    )


def build_get_movie_screenings_query(
    pool: asyncpg.Pool, schema: str
) -> GetMovieScreeningsQuery:
    """Build movie-screening query."""
    return GetMovieScreeningsQuery(
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        ),
        screening_reader=SupabaseScreeningReader(pool=pool, schema=schema),
    )


def build_list_cinema_source_assignments_query(
    pool: asyncpg.Pool, schema: str
) -> ListCinemaSourceAssignmentsQuery:
    """Build cinema-source assignment query."""
    return ListCinemaSourceAssignmentsQuery(
        reader=SupabaseCinemaSourceAssignmentReader(pool=pool, schema=schema)
    )


def build_search_screenings_query(
    pool: asyncpg.Pool, schema: str
) -> SearchScreeningsQuery:
    """Build screening-search query."""
    return SearchScreeningsQuery(
        screening_reader=SupabaseScreeningReader(pool=pool, schema=schema),
        cinema_repository=SupabaseCinemaRepository(
            gateway=SupabaseCinemaGateway(pool=pool, schema=schema)
        ),
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        ),
    )


def build_screening_data_audit_query(
    pool: asyncpg.Pool, schema: str
) -> ScreeningDataAuditQuery:
    """Build the read-only screening data audit query."""
    return ScreeningDataAuditQuery(
        screening_reader=SupabaseScreeningReader(pool=pool, schema=schema)
    )


def build_reconcile_screenings_command(
    pool: asyncpg.Pool, schema: str
) -> ReconcileScreeningsCommand:
    """Build the explicitly guarded screening reconciliation command."""
    return ReconcileScreeningsCommand(
        screening_repository=SupabaseScreeningRepository(
            gateway=SupabaseScreeningGateway(pool=pool, schema=schema)
        )
    )
