"""Dependency injection container.

Central registry for application lifecycle and supported configured use cases.
"""

from __future__ import annotations

from functools import cached_property
from uuid import uuid4

import asyncpg
from dotenv import load_dotenv

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.queries.verify_access_token import VerifyAccessTokenQuery
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.auth import (
    AuthenticateAdministratorUseCase,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
)
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.get_screening import GetScreeningUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.infrastructure.di.auth import (
    build_authenticate_administrator_use_case,
    build_invite_account_use_case,
    build_set_account_role_use_case,
    build_verify_access_token_query,
)
from marquise.infrastructure.di.import_use_cases import (
    build_create_movies_use_case,
    build_create_screenings_use_case,
    build_fetch_screenings_use_case,
    build_import_screenings_use_case,
)
from marquise.infrastructure.di.queries import (
    build_get_cinema_screenings_query,
    build_get_movie_screenings_query,
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

load_dotenv()


class SettingsProvider:
    """Loads settings once from the environment."""

    def __init__(self) -> None:
        import os

        self._settings = Settings(
            database_url=os.environ.get("DATABASE_URL", ""),
            cineplex_api_key=os.environ.get("CINEPLEX_API_KEY", ""),
            schema=os.environ.get("DATABASE_SCHEMA", "marquise"),
            supabase_url=os.environ.get("SUPABASE_URL", ""),
            supabase_publishable_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY", ""),
            supabase_service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

    @property
    def settings(self) -> Settings:
        return self._settings


class Container:
    """Central dependency injection container.

    Typical usage for a delivery command::

        container = Container()
        await container.initialize()
        try:
            result = await container.list_cinemas_use_case.execute(...)
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
            if not self._settings.database_url:
                raise RuntimeError("DATABASE_URL is required")
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
    # Authentication (no database lifecycle required)
    # ------------------------------------------------------------------

    @cached_property
    def _verify_access_token_query(self) -> VerifyAccessTokenQuery:
        return build_verify_access_token_query(self._settings.supabase_url)

    @property
    def _authenticate_administrator_use_case(
        self,
    ) -> AuthenticateAdministratorUseCase:
        return build_authenticate_administrator_use_case(
            self._settings.supabase_url,
            self._settings.supabase_publishable_key,
        )

    @property
    def _invite_account_use_case(self) -> InviteAccountUseCase:
        return build_invite_account_use_case(
            self._settings.supabase_url,
            self._settings.supabase_publishable_key,
            self._settings.supabase_service_role_key,
        )

    @property
    def _set_account_role_use_case(self) -> SetAccountRoleUseCase:
        return build_set_account_role_use_case(
            self._settings.supabase_url,
            self._settings.supabase_publishable_key,
            self._settings.supabase_service_role_key,
        )

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
            self._registry = build_source_registry(self._settings.cineplex_api_key)
        return self._registry

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    @property
    def _cinema_repository(self) -> SupabaseCinemaRepository:
        return SupabaseCinemaRepository(gateway=self._cinema_gateway)

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
        return build_create_source_use_case(self._pool_property, self._schema)

    @property
    def _list_sources_use_case(self) -> ListSourcesUseCase:
        return build_list_sources_use_case(self._pool_property, self._schema)

    @property
    def _list_registry_sources_use_case(self) -> ListRegistrySourcesUseCase:
        return ListRegistrySourcesUseCase(registry=self._source_registry)

    @property
    def _delete_source_use_case(self) -> DeleteSourceUseCase:
        return build_delete_source_use_case(self._pool_property, self._schema)

    @property
    def _assign_source_use_case(self) -> AssignSourceUseCase:
        return build_assign_source_use_case(
            self._pool_property, self._schema, self._cinema_repository
        )

    @property
    def _unassign_source_use_case(self) -> UnassignSourceUseCase:
        return build_unassign_source_use_case(self._pool_property, self._schema)

    @property
    def _get_cinema_source_use_case(self) -> GetCinemaSourceUseCase:
        return build_get_cinema_source_use_case(self._pool_property, self._schema)

    @property
    def _list_cinema_source_assignments_query(
        self,
    ) -> ListCinemaSourceAssignmentsQuery:
        return build_list_cinema_source_assignments_query(
            self._pool_property, self._schema
        )

    @property
    def _fetch_screenings_use_case(self) -> FetchScreeningsFromSourceQuery:
        return build_fetch_screenings_use_case(
            self._pool_property, self._schema, self._source_registry
        )

    @property
    def _create_movies_use_case(self) -> CreateMissingMoviesCommand:
        return build_create_movies_use_case(self._pool_property, self._schema)

    @property
    def _create_screenings_use_case(self) -> CreateScreeningsCommand:
        return build_create_screenings_use_case(self._pool_property, self._schema)

    @property
    def _import_screenings_use_case(self) -> ImportScreeningsCommand:
        return build_import_screenings_use_case(
            fetch_screenings_use_case=self._fetch_screenings_use_case,
            create_movies_use_case=self._create_movies_use_case,
            create_screenings_use_case=self._create_screenings_use_case,
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
    def _get_cinema_screenings_query(self) -> GetCinemaScreeningsQuery:
        return build_get_cinema_screenings_query(self._pool_property, self._schema)

    @property
    def _get_cinema_movies_use_case(self) -> GetCinemaMoviesUseCase:
        return GetCinemaMoviesUseCase(
            cinema_repository=self._cinema_repository,
            screening_repository=self._screening_repository,
        )

    @property
    def _search_screenings_query(self) -> SearchScreeningsQuery:
        return build_search_screenings_query(self._pool_property, self._schema)

    @property
    def _get_screening_use_case(self) -> GetScreeningUseCase:
        return GetScreeningUseCase(screening_repository=self._screening_repository)

    @property
    def _create_screening_use_case(self) -> CreateScreeningUseCase:
        return CreateScreeningUseCase(
            screening_repository=self._screening_repository,
            movie_repository=self._movie_repository,
            cinema_repository=self._cinema_repository,
            id_factory=lambda: str(uuid4()),
        )

    @property
    def _update_screening_use_case(self) -> UpdateScreeningUseCase:
        return UpdateScreeningUseCase(
            screening_repository=self._screening_repository,
            movie_repository=self._movie_repository,
            cinema_repository=self._cinema_repository,
        )

    @property
    def _delete_screening_use_case(self) -> DeleteScreeningUseCase:
        return DeleteScreeningUseCase(screening_repository=self._screening_repository)

    @property
    def _get_movie_screenings_query(self) -> GetMovieScreeningsQuery:
        return build_get_movie_screenings_query(self._pool_property, self._schema)

    # ------------------------------------------------------------------
    # Public use cases
    # ------------------------------------------------------------------

    @property
    def verify_access_token_query(self) -> VerifyAccessTokenQuery:
        """Public configured access-token verification query."""
        return self._verify_access_token_query

    @property
    def authenticate_administrator_use_case(
        self,
    ) -> AuthenticateAdministratorUseCase:
        """Public configured Administrator authentication use case."""
        return self._authenticate_administrator_use_case

    @property
    def invite_account_use_case(self) -> InviteAccountUseCase:
        """Public configured account invitation use case."""
        return self._invite_account_use_case

    @property
    def set_account_role_use_case(self) -> SetAccountRoleUseCase:
        """Public configured account role-change use case."""
        return self._set_account_role_use_case

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
    def list_cinema_source_assignments_query(
        self,
    ) -> ListCinemaSourceAssignmentsQuery:
        """Public cinema-source assignment query."""
        return self._list_cinema_source_assignments_query

    @property
    def create_source_use_case(self) -> CreateSourceUseCase:
        """Public create-source use case."""
        return self._create_source_use_case

    @property
    def list_sources_use_case(self) -> ListSourcesUseCase:
        """Public list-sources use case."""
        return self._list_sources_use_case

    @property
    def delete_source_use_case(self) -> DeleteSourceUseCase:
        """Public delete-source use case."""
        return self._delete_source_use_case

    @property
    def assign_source_use_case(self) -> AssignSourceUseCase:
        """Public assign-source use case."""
        return self._assign_source_use_case

    @property
    def unassign_source_use_case(self) -> UnassignSourceUseCase:
        """Public unassign-source use case."""
        return self._unassign_source_use_case

    @property
    def get_cinema_source_use_case(self) -> GetCinemaSourceUseCase:
        """Public get-cinema-source use case."""
        return self._get_cinema_source_use_case

    @property
    def list_registry_sources_use_case(self) -> ListRegistrySourcesUseCase:
        """Public list-registry-sources use case."""
        _ = self._pool_property
        return self._list_registry_sources_use_case

    @property
    def fetch_screenings_use_case(self) -> FetchScreeningsFromSourceQuery:
        """Public fetch-screenings query."""
        return self._fetch_screenings_use_case

    @property
    def create_movies_use_case(self) -> CreateMissingMoviesCommand:
        """Public create-missing-movies command."""
        return self._create_movies_use_case

    @property
    def create_screenings_use_case(self) -> CreateScreeningsCommand:
        """Public create-screenings command."""
        return self._create_screenings_use_case

    @property
    def import_screenings_use_case(self) -> ImportScreeningsCommand:
        """Public application workflow for importing one cinema."""
        return self._import_screenings_use_case

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
    def get_cinema_screenings_query(self) -> GetCinemaScreeningsQuery:
        """Public cinema-screenings query (no authentication required)."""
        return self._get_cinema_screenings_query

    @property
    def search_screenings_query(self) -> SearchScreeningsQuery:
        """Public search-screenings query (no authentication required)."""
        return self._search_screenings_query

    @property
    def get_screening_use_case(self) -> GetScreeningUseCase:
        """Public get-screening use case (no authentication required)."""
        return self._get_screening_use_case

    @property
    def create_screening_use_case(self) -> CreateScreeningUseCase:
        """Public create-screening use case."""
        return self._create_screening_use_case

    @property
    def update_screening_use_case(self) -> UpdateScreeningUseCase:
        """Public update-screening use case."""
        return self._update_screening_use_case

    @property
    def delete_screening_use_case(self) -> DeleteScreeningUseCase:
        """Public delete-screening use case."""
        return self._delete_screening_use_case

    @property
    def get_movie_screenings_query(self) -> GetMovieScreeningsQuery:
        """Public movie-screenings query (no authentication required)."""
        return self._get_movie_screenings_query

    @property
    def get_cinema_movies_use_case(self) -> GetCinemaMoviesUseCase:
        """Public get-cinema-movies use case (no authentication required)."""
        return self._get_cinema_movies_use_case
