"""Composition root that owns the database lifecycle and wires every use case."""

from __future__ import annotations

import os
import types

import asyncpg
from dotenv import load_dotenv

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
from marquise.infrastructure.di.source_registry import build_source_registry
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.database import Database
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


def _read_settings() -> Settings:
    """Load a local .env file, then read settings from the environment."""
    load_dotenv()
    return Settings(
        database_url=os.environ.get("DATABASE_URL", ""),
        cineplex_api_key=os.environ.get("CINEPLEX_API_KEY", ""),
        tmdb_api_key=os.environ.get("TMDB_API_KEY", ""),
        schema=os.environ.get("DATABASE_SCHEMA", "marquise"),
    )


class MarquiseFactory:
    """Manage database lifecycle and expose configured use cases.

    Typical usage::

        factory = MarquiseFactory()
        await factory.initialize()
        try:
            use_case = factory.list_cinemas_use_case
            result = await use_case.execute(use_case.InputData())
        finally:
            await factory.shutdown()
    """

    def __init__(self) -> None:
        self._settings = _read_settings()
        self._database: Database | None = None
        self._pool: asyncpg.Pool | None = None
        self._registry: SourceRegistry | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Open the database connection pool.

        Must be called before accessing any use case that touches the database.
        Safe to call multiple times (idempotent).

        Raises:
            RuntimeError: If ``DATABASE_URL`` is not configured.
        """
        if self._database is None:
            if not self._settings.database_url:
                raise RuntimeError("DATABASE_URL is required")
            self._database = Database(self._settings)
            await self._database.connect()
            self._pool = self._database.pool

    async def shutdown(self) -> None:
        """Close the database connection pool.

        Safe to call even if :meth:`initialize` was never called.
        """
        if self._database is not None:
            await self._database.disconnect()
            self._database = None
            self._pool = None

    async def check_database_health(self) -> bool:
        """Check whether the database pool can serve queries.

        Returns:
            True if the pool is initialized and a trivial query succeeds,
            False otherwise.
        """
        if self._database is None:
            return False
        return await self._database.ping()

    async def __aenter__(self) -> MarquiseFactory:
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self.shutdown()

    # ------------------------------------------------------------------
    # Shared collaborators
    # ------------------------------------------------------------------

    @property
    def _open_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError(
                "Database pool not available. Call factory.initialize() first."
            )
        return self._pool

    @property
    def _source_registry(self) -> SourceRegistry:
        if self._registry is None:
            self._registry = build_source_registry(self._settings.cineplex_api_key)
        return self._registry

    @property
    def _cinema_repository(self) -> SupabaseCinemaRepository:
        return SupabaseCinemaRepository(
            gateway=SupabaseCinemaGateway(
                pool=self._open_pool, schema=self._settings.schema
            )
        )

    @property
    def _screening_repository(self) -> SupabaseScreeningRepository:
        return SupabaseScreeningRepository(
            gateway=SupabaseScreeningGateway(
                pool=self._open_pool, schema=self._settings.schema
            )
        )

    @property
    def _movie_repository(self) -> SupabaseMovieRepository:
        return SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(
                pool=self._open_pool, schema=self._settings.schema
            )
        )

    # ------------------------------------------------------------------
    # Cinemas
    # ------------------------------------------------------------------

    @property
    def create_cinema_use_case(self) -> CreateCinemaUseCase:
        """Configured use case for creating cinemas."""
        return CreateCinemaUseCase(cinema_repository=self._cinema_repository)

    @property
    def delete_cinema_use_case(self) -> DeleteCinemaUseCase:
        """Configured use case for deleting cinemas."""
        return DeleteCinemaUseCase(cinema_repository=self._cinema_repository)

    @property
    def update_cinema_use_case(self) -> UpdateCinemaUseCase:
        """Configured use case for updating cinemas."""
        return UpdateCinemaUseCase(cinema_repository=self._cinema_repository)

    @property
    def list_cinemas_use_case(self) -> ListCinemasUseCase:
        """Configured use case for listing cinemas."""
        return ListCinemasUseCase(cinema_repository=self._cinema_repository)

    @property
    def get_cinema_use_case(self) -> GetCinemaUseCase:
        """Configured use case for retrieving one cinema."""
        return GetCinemaUseCase(cinema_repository=self._cinema_repository)

    @property
    def get_cinema_movies_use_case(self) -> GetCinemaMoviesUseCase:
        """Configured use case for listing a cinema's movies."""
        return GetCinemaMoviesUseCase(
            cinema_repository=self._cinema_repository,
            screening_repository=self._screening_repository,
        )

    @property
    def get_cinema_screenings_query(self) -> GetCinemaScreeningsQuery:
        """Configured query for listing a cinema's screenings."""
        return build_get_cinema_screenings_query(self._open_pool, self._settings.schema)

    # ------------------------------------------------------------------
    # Movies
    # ------------------------------------------------------------------

    @property
    def list_movies_use_case(self) -> ListMoviesUseCase:
        """Configured use case for listing movies."""
        return ListMoviesUseCase(movie_repository=self._movie_repository)

    @property
    def get_movie_use_case(self) -> GetMovieUseCase:
        """Configured use case for retrieving one movie."""
        return GetMovieUseCase(movie_repository=self._movie_repository)

    @property
    def get_movie_screenings_query(self) -> GetMovieScreeningsQuery:
        """Configured query for listing a movie's screenings."""
        return build_get_movie_screenings_query(self._open_pool, self._settings.schema)

    @property
    def refresh_movies_use_case(self) -> RefreshMoviesUseCase:
        """Configured explicit metadata refresh workflow."""
        return build_refresh_movies_use_case(
            self._open_pool, self._settings.schema, self._settings.tmdb_api_key
        )

    @property
    def merge_movies_use_case(self) -> MergeMoviesUseCase:
        """Configured guarded movie merge workflow."""
        return build_merge_movies_use_case(
            self._open_pool, self._settings.schema, self._settings.tmdb_api_key
        )

    # ------------------------------------------------------------------
    # Screenings
    # ------------------------------------------------------------------

    @property
    def browse_screening_movies_query(self) -> BrowseScreeningMoviesQuery:
        """Configured movie-first screening query."""
        return build_browse_screening_movies_query(
            self._open_pool, self._settings.schema
        )

    @property
    def count_screening_days_query(self) -> CountScreeningDaysQuery:
        """Configured daily screening-count query."""
        return build_count_screening_days_query(self._open_pool, self._settings.schema)

    @property
    def search_screenings_query(self) -> SearchScreeningsQuery:
        """Configured query for searching screenings."""
        return build_search_screenings_query(self._open_pool, self._settings.schema)

    @property
    def get_screening_query(self) -> GetScreeningQuery:
        """Configured query for retrieving one screening."""
        return build_get_screening_query(self._open_pool, self._settings.schema)

    @property
    def import_screenings_use_case(self) -> ImportScreeningsCommand:
        """Configured application workflow for importing one cinema."""
        return build_import_screenings_use_case(
            self._open_pool,
            self._settings.schema,
            self._settings.tmdb_api_key,
            build_fetch_screenings_use_case(
                self._open_pool, self._settings.schema, self._source_registry
            ),
        )

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    @property
    def list_registry_sources_use_case(self) -> ListRegistrySourcesUseCase:
        """Configured use case for listing registry sources."""
        return ListRegistrySourcesUseCase(registry=self._source_registry)

    @property
    def create_source_use_case(self) -> CreateSourceUseCase:
        """Configured use case for registering sources."""
        return build_create_source_use_case(self._open_pool, self._settings.schema)

    @property
    def list_sources_use_case(self) -> ListSourcesUseCase:
        """Configured use case for listing registered sources."""
        return build_list_sources_use_case(self._open_pool, self._settings.schema)

    @property
    def delete_source_use_case(self) -> DeleteSourceUseCase:
        """Configured use case for unregistering sources."""
        return build_delete_source_use_case(self._open_pool, self._settings.schema)

    @property
    def assign_source_use_case(self) -> AssignSourceUseCase:
        """Configured use case for assigning sources."""
        return build_assign_source_use_case(
            self._open_pool, self._settings.schema, self._cinema_repository
        )

    @property
    def unassign_source_use_case(self) -> UnassignSourceUseCase:
        """Configured use case for unassigning sources."""
        return build_unassign_source_use_case(self._open_pool, self._settings.schema)

    @property
    def get_cinema_source_use_case(self) -> GetCinemaSourceUseCase:
        """Configured use case for looking up cinema sources."""
        return build_get_cinema_source_use_case(self._open_pool, self._settings.schema)

    @property
    def list_cinema_source_assignments_query(
        self,
    ) -> ListCinemaSourceAssignmentsQuery:
        """Configured query for cinema-source assignments."""
        return build_list_cinema_source_assignments_query(
            self._open_pool, self._settings.schema
        )
