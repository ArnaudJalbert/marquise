"""Import use-case dependency wiring."""

from __future__ import annotations

import asyncpg

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import SourceRegistryQuery
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.cinema_source_assignment import (
    SupabaseCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)
from marquise.interface_adapters.repositories.supabase.cinema_source_assignment_repository import (  # noqa: E501
    SupabaseCinemaSourceAssignmentRepository,
)
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


def build_fetch_screenings_use_case(
    pool: asyncpg.Pool,
    schema: str,
    source_registry: SourceRegistryQuery,
) -> FetchScreeningsFromSourceQuery:
    """Build source-screening fetch query."""
    return FetchScreeningsFromSourceQuery(
        cinema_repository=SupabaseCinemaRepository(
            gateway=SupabaseCinemaGateway(pool=pool, schema=schema)
        ),
        assignment_repository=SupabaseCinemaSourceAssignmentRepository(
            gateway=SupabaseCinemaSourceAssignmentGateway(pool=pool, schema=schema)
        ),
        source_registry=source_registry,
    )


def build_create_movies_use_case(
    pool: asyncpg.Pool, schema: str
) -> CreateMissingMoviesCommand:
    """Build missing-movie creation command."""
    return CreateMissingMoviesCommand(
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        )
    )


def build_create_screenings_use_case(
    pool: asyncpg.Pool, schema: str
) -> CreateScreeningsCommand:
    """Build screening creation command."""
    return CreateScreeningsCommand(
        screening_repository=SupabaseScreeningRepository(
            gateway=SupabaseScreeningGateway(pool=pool, schema=schema)
        )
    )


def build_import_screenings_use_case(
    fetch_screenings_use_case: FetchScreeningsFromSourceQuery,
    create_movies_use_case: CreateMissingMoviesCommand,
    create_screenings_use_case: CreateScreeningsCommand,
) -> ImportScreeningsCommand:
    """Build the application-level cinema import workflow."""
    return ImportScreeningsCommand(
        fetch_screenings_use_case=fetch_screenings_use_case,
        create_movies_use_case=create_movies_use_case,
        create_screenings_use_case=create_screenings_use_case,
    )
