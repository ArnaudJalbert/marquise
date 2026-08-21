"""Dependency injection container.

Central registry for all application dependencies. Controllers and supported
use cases are exposed as public properties; everything else is private.
"""

from __future__ import annotations

import asyncpg
from dotenv import load_dotenv

from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_screenings import (
    GetCinemaScreeningsUseCase,
)
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.get_movie_screenings import (
    GetMovieScreeningsUseCase,
)
from marquise.application.use_cases.get_screening import GetScreeningUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.search_screenings import SearchScreeningsUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.infrastructure.controllers.movie_controller import MovieController
from marquise.infrastructure.controllers.screening_controller import ScreeningController
from marquise.infrastructure.controllers.source_controller import SourceController
from marquise.infrastructure.sources.cinemacinema.gateways.source import (
    CinemaCinemaSource,
)
from marquise.infrastructure.sources.cinemamoderne.gateways.source import (
    CinemaModerneSource,
)
from marquise.infrastructure.sources.cinemapublic.gateways.source import (
    CinemaPublicSource,
)
from marquise.infrastructure.sources.cinematheque.gateways.source import (
    CinemathequeSource,
)
from marquise.infrastructure.sources.cineplex.gateways.source import (
    CineplexSource,
)
from marquise.infrastructure.sources.outremont.gateways.source import (
    OutremontSource,
)
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.database import Database
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.cinema_source_assignment import (
    SupabaseCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)
from marquise.infrastructure.supabase.gateways.source_definition import (
    SupabaseSourceDefinitionGateway,
)
from marquise.interface_adapters.repositories.source_adapters.cinemacinema import (
    CinemaCinemaAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cinemamoderne import (
    CinemaModerneAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cinemapublic import (
    CinemaPublicAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cinematheque import (
    CinemathequeAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cineplex import (
    CineplexAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.outremont import (
    OutremontAdapter,
)
from marquise.interface_adapters.repositories.source_registry import SourceRegistry
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
from marquise.interface_adapters.repositories.supabase.source_definition_repository import (  # noqa: E501
    SupabaseSourceDefinitionRepository,
)

load_dotenv()


class SettingsProvider:
    """Loads settings once from the environment."""

    def __init__(self) -> None:
        import os

        self._settings = Settings(
            database_url=os.environ["DATABASE_URL"],
            cineplex_api_key=os.environ.get("CINEPLEX_API_KEY", ""),
            schema=os.environ.get("DATABASE_SCHEMA", "marquise"),
        )

    @property
    def settings(self) -> Settings:
        return self._settings


class Container:
    """Central dependency injection container.

    Typical usage for a CLI command::

        container = Container()
        await container.initialize()
        try:
            result = await container.cinema_controller.create(...)
        finally:
            await container.shutdown()

    For auth-only commands (no database needed) the ``initialize`` / ``shutdown``
    steps can be skipped.
    """

    def __init__(self) -> None:
        self._settings_provider = SettingsProvider()
        self._database: Database | None = None
        self._pool: asyncpg.Pool | None = None
        self._registry: SourceRegistry | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Open the database connection pool.

        Must be called before any operation that touches the database.
        Safe to call multiple times (idempotent).
        """
        if self._database is None:
            self._database = Database(self._settings)
            await self._database.connect()
            self._pool = self._database.pool

    async def shutdown(self) -> None:
        """Close the database connection pool.

        Safe to call even if ``initialize`` was never called.
        """
        if self._database is not None:
            await self._database.disconnect()
            self._database = None
            self._pool = None

    async def check_database_health(self) -> bool:
        """Report whether the database pool can currently serve queries.

        Returns:
            True if the pool is initialized and a trivial query succeeds,
            False otherwise (including when ``initialize()`` was never
            called).
        """
        if self._database is None:
            return False
        return await self._database.ping()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    @property
    def _settings(self) -> Settings:
        return self._settings_provider.settings

    @property
    def _schema(self) -> str:
        return self._settings.schema

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    @property
    def _pool_property(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError(
                "Database pool not available — call container.initialize() first"
            )
        return self._pool

    # ------------------------------------------------------------------
    # Gateways
    # ------------------------------------------------------------------

    @property
    def _cinema_gateway(self) -> SupabaseCinemaGateway:
        return SupabaseCinemaGateway(pool=self._pool_property, schema=self._schema)

    @property
    def _source_definition_gateway(self) -> SupabaseSourceDefinitionGateway:
        return SupabaseSourceDefinitionGateway(
            pool=self._pool_property, schema=self._schema
        )

    @property
    def _cinema_source_assignment_gateway(
        self,
    ) -> SupabaseCinemaSourceAssignmentGateway:
        return SupabaseCinemaSourceAssignmentGateway(
            pool=self._pool_property, schema=self._schema
        )

    @property
    def _screening_gateway(self) -> SupabaseScreeningGateway:
        return SupabaseScreeningGateway(pool=self._pool_property, schema=self._schema)

    @property
    def _movie_gateway(self) -> SupabaseMovieGateway:
        return SupabaseMovieGateway(pool=self._pool_property, schema=self._schema)

    # ------------------------------------------------------------------
    # Source Registry (cached)
    # ------------------------------------------------------------------

    @property
    def _source_registry(self) -> SourceRegistry:
        if self._registry is None:
            registry = SourceRegistry()
            registry.register(
                "cinemacinema",
                CinemaCinemaAdapter(CinemaCinemaSource()),
            )
            registry.register(
                "cinemamoderne",
                CinemaModerneAdapter(CinemaModerneSource()),
            )
            registry.register(
                "cinemapublic",
                CinemaPublicAdapter(CinemaPublicSource()),
            )
            registry.register(
                "cinematheque",
                CinemathequeAdapter(CinemathequeSource()),
            )
            registry.register(
                "cineplex",
                CineplexAdapter(
                    CineplexSource(api_key=self._settings.cineplex_api_key)
                ),
            )
            registry.register(
                "outremont",
                OutremontAdapter(OutremontSource()),
            )
            self._registry = registry
        return self._registry

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    @property
    def _cinema_repository(self) -> SupabaseCinemaRepository:
        return SupabaseCinemaRepository(gateway=self._cinema_gateway)

    @property
    def _source_definition_repository(self) -> SupabaseSourceDefinitionRepository:
        return SupabaseSourceDefinitionRepository(
            gateway=self._source_definition_gateway
        )

    @property
    def _cinema_source_assignment_repository(
        self,
    ) -> SupabaseCinemaSourceAssignmentRepository:
        return SupabaseCinemaSourceAssignmentRepository(
            gateway=self._cinema_source_assignment_gateway
        )

    @property
    def _screening_repository(self) -> SupabaseScreeningRepository:
        return SupabaseScreeningRepository(gateway=self._screening_gateway)

    @property
    def _movie_repository(self) -> SupabaseMovieRepository:
        return SupabaseMovieRepository(gateway=self._movie_gateway)

    # ------------------------------------------------------------------
    # Use cases — Cinema
    # ------------------------------------------------------------------

    @property
    def _create_cinema_use_case(self) -> CreateCinemaUseCase:
        return CreateCinemaUseCase(cinema_repository=self._cinema_repository)

    @property
    def _delete_cinema_use_case(self) -> DeleteCinemaUseCase:
        return DeleteCinemaUseCase(cinema_repository=self._cinema_repository)

    @property
    def _list_cinemas_use_case(self) -> ListCinemasUseCase:
        return ListCinemasUseCase(cinema_repository=self._cinema_repository)

    @property
    def _update_cinema_use_case(self) -> UpdateCinemaUseCase:
        return UpdateCinemaUseCase(cinema_repository=self._cinema_repository)

    # ------------------------------------------------------------------
    # Use cases — Source
    # ------------------------------------------------------------------

    @property
    def _create_source_use_case(self) -> CreateSourceUseCase:
        return CreateSourceUseCase(source_repository=self._source_definition_repository)

    @property
    def _list_sources_use_case(self) -> ListSourcesUseCase:
        return ListSourcesUseCase(source_repository=self._source_definition_repository)

    @property
    def _list_registry_sources_use_case(self) -> ListRegistrySourcesUseCase:
        return ListRegistrySourcesUseCase(registry=self._source_registry)

    @property
    def _delete_source_use_case(self) -> DeleteSourceUseCase:
        return DeleteSourceUseCase(source_repository=self._source_definition_repository)

    @property
    def _assign_source_use_case(self) -> AssignSourceUseCase:
        return AssignSourceUseCase(
            cinema_repository=self._cinema_repository,
            source_definition_repository=self._source_definition_repository,
            assignment_repository=self._cinema_source_assignment_repository,
        )

    @property
    def _unassign_source_use_case(self) -> UnassignSourceUseCase:
        return UnassignSourceUseCase(
            assignment_repository=self._cinema_source_assignment_repository
        )

    @property
    def _get_cinema_source_use_case(self) -> GetCinemaSourceUseCase:
        return GetCinemaSourceUseCase(
            assignment_repository=self._cinema_source_assignment_repository,
        )

    @property
    def _fetch_screenings_use_case(self) -> FetchScreeningsFromSourceQuery:
        return FetchScreeningsFromSourceQuery(
            cinema_repository=self._cinema_repository,
            assignment_repository=self._cinema_source_assignment_repository,
            source_registry=self._source_registry,
        )

    @property
    def _create_movies_use_case(self) -> CreateMissingMoviesCommand:
        return CreateMissingMoviesCommand(
            movie_repository=self._movie_repository,
        )

    @property
    def _create_screenings_use_case(self) -> CreateScreeningsCommand:
        return CreateScreeningsCommand(
            screening_repository=self._screening_repository,
        )

    # ------------------------------------------------------------------
    # Use cases — Read-only (public API)
    # ------------------------------------------------------------------

    @property
    def _get_cinema_use_case(self) -> GetCinemaUseCase:
        return GetCinemaUseCase(cinema_repository=self._cinema_repository)

    @property
    def _get_movie_use_case(self) -> GetMovieUseCase:
        return GetMovieUseCase(movie_repository=self._movie_repository)

    @property
    def _list_movies_use_case(self) -> ListMoviesUseCase:
        return ListMoviesUseCase(movie_repository=self._movie_repository)

    @property
    def _get_cinema_screenings_use_case(self) -> GetCinemaScreeningsUseCase:
        return GetCinemaScreeningsUseCase(
            cinema_repository=self._cinema_repository,
            screening_repository=self._screening_repository,
        )

    @property
    def _get_cinema_movies_use_case(self) -> GetCinemaMoviesUseCase:
        return GetCinemaMoviesUseCase(
            cinema_repository=self._cinema_repository,
            screening_repository=self._screening_repository,
        )

    @property
    def _search_screenings_use_case(self) -> SearchScreeningsUseCase:
        return SearchScreeningsUseCase(
            screening_repository=self._screening_repository,
            cinema_repository=self._cinema_repository,
            movie_repository=self._movie_repository,
        )

    @property
    def _get_screening_use_case(self) -> GetScreeningUseCase:
        return GetScreeningUseCase(screening_repository=self._screening_repository)

    @property
    def _get_movie_screenings_use_case(self) -> GetMovieScreeningsUseCase:
        return GetMovieScreeningsUseCase(
            movie_repository=self._movie_repository,
            screening_repository=self._screening_repository,
        )

    # ------------------------------------------------------------------
    # Public use cases
    # ------------------------------------------------------------------

    @property
    def create_cinema_use_case(self) -> CreateCinemaUseCase:
        """Public create-cinema use case."""
        return self._create_cinema_use_case

    @property
    def delete_cinema_use_case(self) -> DeleteCinemaUseCase:
        """Public delete-cinema use case."""
        return self._delete_cinema_use_case

    @property
    def update_cinema_use_case(self) -> UpdateCinemaUseCase:
        """Public update-cinema use case."""
        return self._update_cinema_use_case

    @property
    def list_cinemas_use_case(self) -> ListCinemasUseCase:
        """Public list-cinemas use case (no authentication required)."""
        return self._list_cinemas_use_case

    @property
    def get_cinema_use_case(self) -> GetCinemaUseCase:
        """Public get-cinema use case (no authentication required)."""
        return self._get_cinema_use_case

    @property
    def get_movie_use_case(self) -> GetMovieUseCase:
        """Public get-movie use case (no authentication required)."""
        return self._get_movie_use_case

    @property
    def list_movies_use_case(self) -> ListMoviesUseCase:
        """Public list-movies use case (no authentication required)."""
        return self._list_movies_use_case

    @property
    def get_cinema_screenings_use_case(self) -> GetCinemaScreeningsUseCase:
        """Public get-cinema-screenings use case (no authentication required)."""
        return self._get_cinema_screenings_use_case

    @property
    def search_screenings_use_case(self) -> SearchScreeningsUseCase:
        """Public search-screenings use case (no authentication required)."""
        return self._search_screenings_use_case

    @property
    def get_screening_use_case(self) -> GetScreeningUseCase:
        """Public get-screening use case (no authentication required)."""
        return self._get_screening_use_case

    @property
    def get_movie_screenings_use_case(self) -> GetMovieScreeningsUseCase:
        """Public get-movie-screenings use case (no authentication required)."""
        return self._get_movie_screenings_use_case

    @property
    def get_cinema_movies_use_case(self) -> GetCinemaMoviesUseCase:
        """Public get-cinema-movies use case (no authentication required)."""
        return self._get_cinema_movies_use_case

    # ------------------------------------------------------------------
    # Controllers (public)
    # ------------------------------------------------------------------

    @property
    def cinema_controller(self) -> CinemaController:
        return CinemaController(
            get_cinema_use_case=self._get_cinema_use_case,
            get_cinema_movies_use_case=self._get_cinema_movies_use_case,
            get_cinema_screenings_use_case=self._get_cinema_screenings_use_case,
            list_cinemas_use_case=self._list_cinemas_use_case,
        )

    @property
    def movie_controller(self) -> MovieController:
        return MovieController(
            get_movie_use_case=self._get_movie_use_case,
            get_movie_screenings_use_case=self._get_movie_screenings_use_case,
            list_movies_use_case=self._list_movies_use_case,
        )

    @property
    def screening_controller(self) -> ScreeningController:
        return ScreeningController(
            get_screening_use_case=self._get_screening_use_case,
            search_screenings_use_case=self._search_screenings_use_case,
        )

    @property
    def source_controller(self) -> SourceController:
        return SourceController(
            create_source_use_case=self._create_source_use_case,
            list_sources_use_case=self._list_sources_use_case,
            delete_source_use_case=self._delete_source_use_case,
            assign_source_use_case=self._assign_source_use_case,
            unassign_source_use_case=self._unassign_source_use_case,
            get_cinema_source_use_case=self._get_cinema_source_use_case,
            list_registry_sources_use_case=self._list_registry_sources_use_case,
            fetch_screenings_use_case=self._fetch_screenings_use_case,
            create_movies_use_case=self._create_movies_use_case,
            create_screenings_use_case=self._create_screenings_use_case,
        )
