"""Wired use cases grouped by area, one immutable container per area."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.queries.count_screening_days import CountScreeningDaysQuery
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.merge_movies import MergeMoviesUseCase
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.di.import_use_cases import (
    build_fetch_screenings_use_case,
    build_import_screenings_use_case,
    build_merge_movies_use_case,
    build_refresh_movies_use_case,
)
from marquise.infrastructure.di.queries import (
    build_browse_screening_movies_query,
    build_count_screening_days_query,
    build_get_cinema_screenings_query,
    build_get_movie_screenings_query,
    build_get_screening_query,
    build_list_cinema_source_assignments_query,
    build_search_screenings_query,
)
from marquise.infrastructure.di.source_management import (
    build_assign_source_use_case,
    build_create_source_use_case,
    build_delete_source_use_case,
    build_get_cinema_source_use_case,
    build_list_sources_use_case,
    build_unassign_source_use_case,
)
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)
from marquise.interface_adapters.repositories.source_registry import SourceRegistry
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


@dataclass(frozen=True, slots=True)
class CinemaUseCases:
    """Wired use cases and queries that read and change cinemas."""

    create_cinema_use_case: CreateCinemaUseCase
    delete_cinema_use_case: DeleteCinemaUseCase
    update_cinema_use_case: UpdateCinemaUseCase
    list_cinemas_use_case: ListCinemasUseCase
    get_cinema_use_case: GetCinemaUseCase
    get_cinema_movies_use_case: GetCinemaMoviesUseCase
    get_cinema_screenings_query: GetCinemaScreeningsQuery


@dataclass(frozen=True, slots=True)
class MovieUseCases:
    """Wired use cases and queries that read, refresh and merge movies."""

    list_movies_use_case: ListMoviesUseCase
    get_movie_use_case: GetMovieUseCase
    get_movie_screenings_query: GetMovieScreeningsQuery
    refresh_movies_use_case: RefreshMoviesUseCase
    merge_movies_use_case: MergeMoviesUseCase


@dataclass(frozen=True, slots=True)
class ScreeningUseCases:
    """Wired queries that read screenings and the command that imports them."""

    browse_screening_movies_query: BrowseScreeningMoviesQuery
    count_screening_days_query: CountScreeningDaysQuery
    search_screenings_query: SearchScreeningsQuery
    get_screening_query: GetScreeningQuery
    import_screenings_command: ImportScreeningsCommand


@dataclass(frozen=True, slots=True)
class SourceUseCases:
    """Wired use cases and queries that manage sources and their assignments."""

    list_registry_sources_use_case: ListRegistrySourcesUseCase
    create_source_use_case: CreateSourceUseCase
    list_sources_use_case: ListSourcesUseCase
    delete_source_use_case: DeleteSourceUseCase
    assign_source_use_case: AssignSourceUseCase
    unassign_source_use_case: UnassignSourceUseCase
    get_cinema_source_use_case: GetCinemaSourceUseCase
    list_cinema_source_assignments_query: ListCinemaSourceAssignmentsQuery


def _cinema_repository(pool: asyncpg.Pool, schema: str) -> SupabaseCinemaRepository:
    """Build the cinema repository over its Supabase gateway."""
    return SupabaseCinemaRepository(
        gateway=SupabaseCinemaGateway(pool=pool, schema=schema)
    )


def build_cinema_use_cases(pool: asyncpg.Pool, settings: Settings) -> CinemaUseCases:
    """Wire every cinema use case and query.

    Args:
        pool: Open connection pool shared by every gateway.
        settings: Settings that name the database schema.

    Returns:
        The cinema use cases, all sharing one cinema repository.
    """
    cinema_repository = _cinema_repository(pool, settings.schema)
    return CinemaUseCases(
        create_cinema_use_case=CreateCinemaUseCase(cinema_repository=cinema_repository),
        delete_cinema_use_case=DeleteCinemaUseCase(cinema_repository=cinema_repository),
        update_cinema_use_case=UpdateCinemaUseCase(cinema_repository=cinema_repository),
        list_cinemas_use_case=ListCinemasUseCase(cinema_repository=cinema_repository),
        get_cinema_use_case=GetCinemaUseCase(cinema_repository=cinema_repository),
        get_cinema_movies_use_case=GetCinemaMoviesUseCase(
            cinema_repository=cinema_repository,
            screening_repository=SupabaseScreeningRepository(
                gateway=SupabaseScreeningGateway(pool=pool, schema=settings.schema)
            ),
        ),
        get_cinema_screenings_query=build_get_cinema_screenings_query(
            pool, settings.schema
        ),
    )


def build_movie_use_cases(pool: asyncpg.Pool, settings: Settings) -> MovieUseCases:
    """Wire every movie use case and query.

    Args:
        pool: Open connection pool shared by every gateway.
        settings: Settings that name the database schema and the TMDB API key.

    Returns:
        The movie use cases, all sharing one movie repository.
    """
    movie_repository = SupabaseMovieRepository(
        gateway=SupabaseMovieGateway(pool=pool, schema=settings.schema)
    )
    return MovieUseCases(
        list_movies_use_case=ListMoviesUseCase(movie_repository=movie_repository),
        get_movie_use_case=GetMovieUseCase(movie_repository=movie_repository),
        get_movie_screenings_query=build_get_movie_screenings_query(
            pool, settings.schema
        ),
        refresh_movies_use_case=build_refresh_movies_use_case(
            pool, settings.schema, settings.tmdb_api_key
        ),
        merge_movies_use_case=build_merge_movies_use_case(
            pool, settings.schema, settings.tmdb_api_key
        ),
    )


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
        list_sources_use_case=build_list_sources_use_case(pool, schema),
        delete_source_use_case=build_delete_source_use_case(pool, schema),
        assign_source_use_case=build_assign_source_use_case(
            pool, schema, _cinema_repository(pool, schema)
        ),
        unassign_source_use_case=build_unassign_source_use_case(pool, schema),
        get_cinema_source_use_case=build_get_cinema_source_use_case(pool, schema),
        list_cinema_source_assignments_query=(
            build_list_cinema_source_assignments_query(pool, schema)
        ),
    )
