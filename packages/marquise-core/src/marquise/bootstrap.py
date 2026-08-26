"""Public bootstrap API for Marquise.

Provides :class:`MarquiseFactory` — the single entry point for external
consumers (apps) to obtain fully-wired controllers and supported use cases.
Internal code may continue to use the
:class:`~marquise.infrastructure.di.container.Container`
directly.
"""

from __future__ import annotations

import types
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.infrastructure.controllers.movie_controller import MovieController
from marquise.infrastructure.controllers.screening_controller import ScreeningController
from marquise.infrastructure.di.container import Container


class MarquiseFactory:
    """Factory for obtaining fully-wired controllers.

    Handles database lifecycle (pool open/close) and exposes controllers
    as properties.  Typical usage::

        factory = MarquiseFactory()
        await factory.initialize()
        try:
            result = await factory.cinema.list()
        finally:
            await factory.shutdown()

    Or as an async context manager::

        async with MarquiseFactory() as f:
            result = await f.cinema.list()
    """

    def __init__(self) -> None:
        self._container = Container()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Open the database connection pool.

        Must be called before accessing any controller property.
        Safe to call multiple times (idempotent).
        """
        await self._container.initialize()

    async def shutdown(self) -> None:
        """Close the database connection pool.

        Safe to call even if :meth:`initialize` was never called.
        """
        await self._container.shutdown()

    async def check_database_health(self) -> bool:
        """Check whether the database pool can serve queries.

        Returns:
            True if the pool is initialized and a trivial query succeeds,
            False otherwise.
        """
        return await self._container.check_database_health()

    # ------------------------------------------------------------------
    # Controllers and use cases (read-only properties)
    # ------------------------------------------------------------------

    @property
    def create_cinema_use_case(self) -> CreateCinemaUseCase:
        """Configured use case for creating cinemas."""
        return self._container.create_cinema_use_case

    @property
    def delete_cinema_use_case(self) -> DeleteCinemaUseCase:
        """Configured use case for deleting cinemas."""
        return self._container.delete_cinema_use_case

    @property
    def update_cinema_use_case(self) -> UpdateCinemaUseCase:
        """Configured use case for updating cinemas."""
        return self._container.update_cinema_use_case

    @property
    def list_cinema_source_assignments_query(
        self,
    ) -> ListCinemaSourceAssignmentsQuery:
        """Configured query for cinema-source assignments."""
        return self._container.list_cinema_source_assignments_query

    @property
    def create_source_use_case(self) -> CreateSourceUseCase:
        """Configured use case for registering sources."""
        return self._container.create_source_use_case

    @property
    def list_sources_use_case(self) -> ListSourcesUseCase:
        """Configured use case for listing registered sources."""
        return self._container.list_sources_use_case

    @property
    def delete_source_use_case(self) -> DeleteSourceUseCase:
        """Configured use case for unregistering sources."""
        return self._container.delete_source_use_case

    @property
    def assign_source_use_case(self) -> AssignSourceUseCase:
        """Configured use case for assigning sources."""
        return self._container.assign_source_use_case

    @property
    def unassign_source_use_case(self) -> UnassignSourceUseCase:
        """Configured use case for unassigning sources."""
        return self._container.unassign_source_use_case

    @property
    def get_cinema_source_use_case(self) -> GetCinemaSourceUseCase:
        """Configured use case for looking up cinema sources."""
        return self._container.get_cinema_source_use_case

    @property
    def list_registry_sources_use_case(self) -> ListRegistrySourcesUseCase:
        """Configured use case for listing registry sources."""
        return self._container.list_registry_sources_use_case

    @property
    def fetch_screenings_use_case(self) -> FetchScreeningsFromSourceQuery:
        """Configured query for fetching source screenings."""
        return self._container.fetch_screenings_use_case

    @property
    def create_movies_use_case(self) -> CreateMissingMoviesCommand:
        """Configured command for creating missing movies."""
        return self._container.create_movies_use_case

    @property
    def create_screenings_use_case(self) -> CreateScreeningsCommand:
        """Configured command for creating screenings."""
        return self._container.create_screenings_use_case

    @property
    def import_screenings_use_case(self) -> ImportScreeningsCommand:
        """Configured command for importing screenings."""
        return self._container.import_screenings_use_case

    @property
    def cinema(self) -> CinemaController:
        """Cinema management controller."""
        return self._container.cinema_controller

    @property
    def movie(self) -> MovieController:
        """Movie read controller."""
        return self._container.movie_controller

    @property
    def screening(self) -> ScreeningController:
        """Screening read controller."""
        return self._container.screening_controller

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

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


async def create_factory() -> MarquiseFactory:
    """Create and initialize a :class:`MarquiseFactory`.

    Returns:
        A fully-initialized factory ready to serve controller requests.
    """
    factory = MarquiseFactory()
    await factory.initialize()
    return factory


@asynccontextmanager
async def create_factory_session() -> AsyncGenerator[MarquiseFactory]:
    """Context-manager variant of :func:`create_factory`.

    Automatically shuts down the factory when the ``async with`` block exits::

        async with create_factory_session() as f:
            result = await f.cinema.list()
    """
    factory = MarquiseFactory()
    await factory.initialize()
    try:
        yield factory
    finally:
        await factory.shutdown()
