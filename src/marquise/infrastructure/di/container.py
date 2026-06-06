"""Dependency injection container.

Central registry for all application dependencies.  Only controllers are
exposed as public properties — everything else is private to the container.
"""

from __future__ import annotations

from typing import Optional

import asyncpg
from dotenv import load_dotenv

from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.auth.supabase_auth_service import SupabaseAuthService
from marquise.infrastructure.controllers.auth_controller import AuthController
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.database import Database
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)

load_dotenv()


class SettingsProvider:
    """Loads settings once from the environment."""

    def __init__(self) -> None:
        import os

        self._settings = Settings(
            database_url=os.environ["DATABASE_URL"],
            supabase_url=os.environ["SUPABASE_URL"],
            supabase_publishable_key=os.environ["SUPABASE_PUBLISHABLE_KEY"],
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
        self._database: Optional[Database] = None
        self._pool: Optional[asyncpg.Pool] = None

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

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    @property
    def _settings(self) -> Settings:
        return self._settings_provider.settings

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @property
    def _auth_service(self) -> SupabaseAuthService:
        return SupabaseAuthService(
            supabase_url=self._settings.supabase_url,
            publishable_key=self._settings.supabase_publishable_key,
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
        return SupabaseCinemaGateway(pool=self._pool_property)

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    @property
    def _cinema_repository(self) -> SupabaseCinemaRepository:
        return SupabaseCinemaRepository(gateway=self._cinema_gateway)

    # ------------------------------------------------------------------
    # Use cases
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
    # Controllers (public)
    # ------------------------------------------------------------------

    @property
    def auth_controller(self) -> AuthController:
        return AuthController(auth_service=self._auth_service)

    @property
    def cinema_controller(self) -> CinemaController:
        return CinemaController(
            auth_controller=self.auth_controller,
            create_cinema_use_case=self._create_cinema_use_case,
            delete_cinema_use_case=self._delete_cinema_use_case,
            list_cinemas_use_case=self._list_cinemas_use_case,
            update_cinema_use_case=self._update_cinema_use_case,
        )
