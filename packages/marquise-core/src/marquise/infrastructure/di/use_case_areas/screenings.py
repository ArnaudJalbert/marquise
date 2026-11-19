"""Wired screening queries and the screening import command."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.queries.count_screening_days import CountScreeningDaysQuery
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.infrastructure.di.import_use_cases import (
    build_fetch_screenings_use_case,
    build_import_screenings_use_case,
)
from marquise.infrastructure.di.queries import (
    build_browse_screening_movies_query,
    build_count_screening_days_query,
    build_get_screening_query,
    build_search_screenings_query,
)
from marquise.infrastructure.postgres.config.settings import Settings
from marquise.interface_adapters.repositories.source_registry import SourceRegistry


@dataclass(frozen=True, slots=True)
class ScreeningUseCases:
    """Wired queries that read screenings and the command that imports them."""

    browse_screening_movies_query: BrowseScreeningMoviesQuery
    count_screening_days_query: CountScreeningDaysQuery
    search_screenings_query: SearchScreeningsQuery
    get_screening_query: GetScreeningQuery
    import_screenings_command: ImportScreeningsCommand


def build_screening_use_cases(
    pool: asyncpg.Pool, settings: Settings, source_registry: SourceRegistry
) -> ScreeningUseCases:
    """Wire every screening query and the screening import command.

    Args:
        pool: Open connection pool shared by every gateway.
        settings: Settings that name the database schema and the TMDB API key.
        source_registry: Registry the import reads showtimes from.

    Returns:
        The screening use cases.
    """
    return ScreeningUseCases(
        browse_screening_movies_query=build_browse_screening_movies_query(
            pool, settings.schema
        ),
        count_screening_days_query=build_count_screening_days_query(
            pool, settings.schema
        ),
        search_screenings_query=build_search_screenings_query(pool, settings.schema),
        get_screening_query=build_get_screening_query(pool, settings.schema),
        import_screenings_command=build_import_screenings_use_case(
            pool,
            settings.schema,
            settings.tmdb_api_key,
            build_fetch_screenings_use_case(pool, settings.schema, source_registry),
        ),
    )
