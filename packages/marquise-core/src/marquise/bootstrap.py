"""Public bootstrap API for configured Marquise use cases."""

from __future__ import annotations

import types
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.queries.count_screening_days import CountScreeningDaysQuery
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.get_screening import GetScreeningQuery
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
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.application.use_cases.write_screening import WriteScreeningUseCase
from marquise.infrastructure.di.container import Container


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
        self._container = Container()

    @property
    def verify_access_token_query(self) -> VerifyAccessTokenQuery:
        """Configured access-token verification query."""
        return self._container.verify_access_token_query

    @property
    def authenticate_administrator_use_case(
        self,
    ) -> AuthenticateAdministratorUseCase:
        """Configured Administrator authentication use case."""
        return self._container.authenticate_administrator_use_case

    @property
    def invite_account_use_case(self) -> InviteAccountUseCase:
        """Configured account invitation use case."""
        return self._container.invite_account_use_case

    @property
    def set_account_role_use_case(self) -> SetAccountRoleUseCase:
        """Configured account role-change use case."""
        return self._container.set_account_role_use_case

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Open the database connection pool.

        Must be called before accessing any configured use case.
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
    # Configured use cases (read-only properties)
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
    def list_cinemas_use_case(self) -> ListCinemasUseCase:
        """Configured use case for listing cinemas."""
        return self._container.list_cinemas_use_case

    @property
    def get_cinema_use_case(self) -> GetCinemaUseCase:
        """Configured use case for retrieving one cinema."""
        return self._container.get_cinema_use_case

    @property
    def get_cinema_screenings_query(self) -> GetCinemaScreeningsQuery:
        """Configured query for listing a cinema's screenings."""
        return self._container.get_cinema_screenings_query

    @property
    def get_cinema_movies_use_case(self) -> GetCinemaMoviesUseCase:
        """Configured use case for listing a cinema's movies."""
        return self._container.get_cinema_movies_use_case

    @property
    def list_movies_use_case(self) -> ListMoviesUseCase:
        """Configured use case for listing movies."""
        return self._container.list_movies_use_case

    @property
    def get_movie_use_case(self) -> GetMovieUseCase:
        """Configured use case for retrieving one movie."""
        return self._container.get_movie_use_case

    @property
    def get_movie_screenings_query(self) -> GetMovieScreeningsQuery:
        """Configured query for listing a movie's screenings."""
        return self._container.get_movie_screenings_query

    @property
    def browse_screening_movies_query(self) -> BrowseScreeningMoviesQuery:
        """Configured movie-first screening query."""
        return self._container.browse_screening_movies_query

    @property
    def count_screening_days_query(self) -> CountScreeningDaysQuery:
        """Configured daily screening-count query."""
        return self._container.count_screening_days_query

    @property
    def search_screenings_query(self) -> SearchScreeningsQuery:
        """Configured query for searching screenings."""
        return self._container.search_screenings_query

    @property
    def get_screening_query(self) -> GetScreeningQuery:
        """Configured query for retrieving one screening."""
        return self._container.get_screening_query

    @property
    def write_screening_use_case(self) -> WriteScreeningUseCase:
        """Configured audited, retry-safe screening mutation orchestration."""
        return self._container.write_screening_use_case

    @property
    def create_screening_use_case(self) -> CreateScreeningUseCase:
        """Configured use case for creating one screening."""
        return self._container.create_screening_use_case

    @property
    def update_screening_use_case(self) -> UpdateScreeningUseCase:
        """Configured use case for updating one screening."""
        return self._container.update_screening_use_case

    @property
    def delete_screening_use_case(self) -> DeleteScreeningUseCase:
        """Configured use case for deleting one screening."""
        return self._container.delete_screening_use_case

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
        """Configured application workflow for importing one cinema."""
        return self._container.import_screenings_use_case

    @property
    def refresh_movies_use_case(self) -> RefreshMoviesUseCase:
        """Configured explicit metadata refresh workflow."""
        return self._container.refresh_movies_use_case

    @property
    def merge_movies_use_case(self) -> MergeMoviesUseCase:
        """Configured guarded movie merge workflow."""
        return self._container.merge_movies_use_case

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
        A fully initialized factory ready to execute configured use cases.
    """
    factory = MarquiseFactory()
    await factory.initialize()
    return factory


@asynccontextmanager
async def create_factory_session() -> AsyncGenerator[MarquiseFactory]:
    """Context-manager variant of :func:`create_factory`.

    Automatically shuts down factory when ``async with`` block exits::

        async with create_factory_session() as factory:
            use_case = factory.list_cinemas_use_case
            result = await use_case.execute(use_case.InputData())
    """
    factory = MarquiseFactory()
    await factory.initialize()
    try:
        yield factory
    finally:
        await factory.shutdown()
