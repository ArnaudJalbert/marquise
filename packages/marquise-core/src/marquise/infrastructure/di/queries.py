"""Read-query dependency wiring."""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.queries.count_screening_days import CountScreeningDaysQuery
from marquise.application.queries.get_cinema_screenings import GetCinemaScreeningsQuery
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening_movie_reader import (
    SupabaseScreeningMovieReadGateway,
)
from marquise.infrastructure.supabase.gateways.screening_reader import (
    SupabaseScreeningReadGateway,
)
from marquise.interface_adapters.readers.cinema_source_assignment_reader import (
    SupabaseCinemaSourceAssignmentReader,
)
from marquise.interface_adapters.readers.screening_movie_reader import (
    SupabaseScreeningMovieReader,
)
from marquise.interface_adapters.readers.screening_reader import SupabaseScreeningReader
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)


def _screening_reader(pool: asyncpg.Pool, schema: str) -> SupabaseScreeningReader:
    """Build the screening display reader."""
    return SupabaseScreeningReader(
        gateway=SupabaseScreeningReadGateway(pool=pool, schema=schema)
    )


def _screening_movie_reader(
    pool: asyncpg.Pool, schema: str
) -> SupabaseScreeningMovieReader:
    """Build the movie-first screening reader."""
    return SupabaseScreeningMovieReader(
        gateway=SupabaseScreeningMovieReadGateway(pool, schema)
    )


def build_get_screening_query(pool: asyncpg.Pool, schema: str) -> GetScreeningQuery:
    """Build the single-screening query with its display reader."""
    return GetScreeningQuery(screening_reader=_screening_reader(pool, schema))


def build_get_cinema_screenings_query(
    pool: asyncpg.Pool, schema: str
) -> GetCinemaScreeningsQuery:
    """Build cinema-screening query."""
    return GetCinemaScreeningsQuery(
        cinema_repository=SupabaseCinemaRepository(
            gateway=SupabaseCinemaGateway(pool=pool, schema=schema)
        ),
        screening_reader=_screening_reader(pool, schema),
    )


def build_get_movie_screenings_query(
    pool: asyncpg.Pool, schema: str
) -> GetMovieScreeningsQuery:
    """Build movie-screening query."""
    return GetMovieScreeningsQuery(
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        ),
        screening_reader=_screening_reader(pool, schema),
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
        screening_reader=_screening_reader(pool, schema),
        cinema_repository=SupabaseCinemaRepository(
            gateway=SupabaseCinemaGateway(pool=pool, schema=schema)
        ),
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        ),
    )


def build_browse_screening_movies_query(
    pool: asyncpg.Pool, schema: str
) -> BrowseScreeningMoviesQuery:
    """Build the movie-first reader and inject the request clock."""
    return BrowseScreeningMoviesQuery(
        reader=_screening_movie_reader(pool, schema),
        clock=lambda: datetime.now(UTC),
    )


def build_count_screening_days_query(
    pool: asyncpg.Pool, schema: str
) -> CountScreeningDaysQuery:
    """Build the daily screening-count reader and inject the request clock."""
    return CountScreeningDaysQuery(
        reader=_screening_movie_reader(pool, schema),
        clock=lambda: datetime.now(UTC),
    )
