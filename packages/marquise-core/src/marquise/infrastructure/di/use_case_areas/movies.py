"""Wired movie use cases and queries."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.merge_movies import MergeMoviesUseCase
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase
from marquise.infrastructure.di.import_use_cases import (
    build_merge_movies_use_case,
    build_refresh_movies_use_case,
)
from marquise.infrastructure.di.queries import build_get_movie_screenings_query
from marquise.infrastructure.postgres.config.settings import Settings
from marquise.infrastructure.postgres.gateways.movie import PostgresMovieGateway
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)


@dataclass(frozen=True, slots=True)
class MovieUseCases:
    """Wired use cases and queries that read, refresh and merge movies."""

    list_movies_use_case: ListMoviesUseCase
    get_movie_use_case: GetMovieUseCase
    get_movie_screenings_query: GetMovieScreeningsQuery
    refresh_movies_use_case: RefreshMoviesUseCase
    merge_movies_use_case: MergeMoviesUseCase


def build_movie_use_cases(pool: asyncpg.Pool, settings: Settings) -> MovieUseCases:
    """Wire every movie use case and query.

    Args:
        pool: Open connection pool shared by every gateway.
        settings: Settings that name the database schema and the TMDB API key.

    Returns:
        The movie use cases, all sharing one movie repository.
    """
    movie_repository = SupabaseMovieRepository(
        gateway=PostgresMovieGateway(pool=pool, schema=settings.schema)
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
