"""Composition root that wires every use case over an open database."""

from __future__ import annotations

from marquise.infrastructure.di.source_registry import build_source_registry
from marquise.infrastructure.di.use_case_areas import (
    build_cinema_use_cases,
    build_movie_use_cases,
    build_screening_use_cases,
    build_source_use_cases,
)
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.database import Database


class MarquiseFactory:
    """Expose every wired use case, grouped by area.

    The factory receives a database that is already connected and wires each
    use case once. Get one from create_factory_session, which also closes the
    database.

    Attributes:
        cinemas: Cinema use cases and queries.
        movies: Movie use cases and queries.
        screenings: Screening queries and the screening import command.
        sources: Source and cinema-source assignment use cases and queries.

    Example:
        async with create_factory_session() as factory:
            use_case = factory.cinemas.list_cinemas_use_case
            result = await use_case.execute(use_case.InputData(page=1, size=50))
    """

    def __init__(self, settings: Settings, database: Database) -> None:
        """Wire every use case over the connected database.

        Args:
            settings: Settings that name the schema and the TMDB API key.
            database: Database whose pool is already open.
        """
        self._database = database
        pool = database.pool
        source_registry = build_source_registry()
        self.cinemas = build_cinema_use_cases(pool, settings)
        self.movies = build_movie_use_cases(pool, settings)
        self.screenings = build_screening_use_cases(pool, settings, source_registry)
        self.sources = build_source_use_cases(pool, settings, source_registry)

    async def check_database_health(self) -> bool:
        """Check whether the database pool can serve queries.

        Returns:
            True if a trivial query succeeds, False otherwise.
        """
        return await self._database.ping()
