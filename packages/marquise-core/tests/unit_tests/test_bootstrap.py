"""Tests for MarquiseFactory bootstrap API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.queries.get_movie_screenings import (
    GetMovieScreeningsQuery,
)
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.get_screening import GetScreeningUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.bootstrap import MarquiseFactory, create_factory, create_factory_session


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables before each test."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_and_shutdown() -> None:
    """Verify initialize opens the pool and shutdown closes it."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        mock_database.connect.assert_awaited_once()

        await factory.shutdown()
        mock_database.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_safe_when_not_initialized() -> None:
    """Verify shutdown does not raise when initialize was never called."""
    factory = MarquiseFactory()
    await factory.shutdown()


@pytest.mark.asyncio
async def test_initialize_is_idempotent() -> None:
    """Verify calling initialize twice only creates one pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        await factory.initialize()

        mock_database.connect.assert_awaited_once()

        await factory.shutdown()


# ------------------------------------------------------------------
# Configured use-case properties
# ------------------------------------------------------------------


def test_create_cinema_use_case_requires_initialize() -> None:
    """Verify create use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.create_cinema_use_case


@pytest.mark.asyncio
async def test_create_cinema_use_case_returns_configured_use_case() -> None:
    """Verify factory returns create use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.create_cinema_use_case
        assert isinstance(use_case, CreateCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_delete_cinema_use_case_requires_initialize() -> None:
    """Verify delete use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.delete_cinema_use_case


@pytest.mark.asyncio
async def test_delete_cinema_use_case_returns_configured_use_case() -> None:
    """Verify factory returns delete use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.delete_cinema_use_case
        assert isinstance(use_case, DeleteCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_update_cinema_use_case_requires_initialize() -> None:
    """Verify update use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.update_cinema_use_case


@pytest.mark.asyncio
async def test_update_cinema_use_case_returns_configured_use_case() -> None:
    """Verify factory returns update use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.update_cinema_use_case
        assert isinstance(use_case, UpdateCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_list_cinemas_use_case_requires_initialize() -> None:
    """Verify list use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.list_cinemas_use_case


@pytest.mark.asyncio
async def test_list_cinemas_use_case_returns_configured_use_case() -> None:
    """Verify factory returns list use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.list_cinemas_use_case
        assert isinstance(use_case, ListCinemasUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_list_cinema_source_assignments_query_requires_initialize() -> None:
    """Verify assignment query retains pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.list_cinema_source_assignments_query


@pytest.mark.asyncio
async def test_list_assignments_query_returns_configured_query() -> None:
    """Verify factory returns assignment query wired to database pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        query = factory.list_cinema_source_assignments_query
        assert isinstance(query, ListCinemaSourceAssignmentsQuery)
        assert query._reader._pool is mock_database.pool

        await factory.shutdown()


@pytest.mark.parametrize(
    "property_name",
    [
        "create_source_use_case",
        "list_sources_use_case",
        "delete_source_use_case",
        "assign_source_use_case",
        "unassign_source_use_case",
        "get_cinema_source_use_case",
        "list_registry_sources_use_case",
        "fetch_screenings_use_case",
        "create_movies_use_case",
        "create_screenings_use_case",
        "get_cinema_use_case",
        "get_cinema_screenings_query",
        "get_cinema_movies_use_case",
        "list_movies_use_case",
        "get_movie_use_case",
        "get_movie_screenings_query",
        "search_screenings_query",
        "get_screening_use_case",
    ],
)
def test_configured_use_cases_require_initialize(property_name: str) -> None:
    """Verify configured use cases retain pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = getattr(factory, property_name)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("property_name", "use_case_type"),
    [
        ("create_source_use_case", CreateSourceUseCase),
        ("list_sources_use_case", ListSourcesUseCase),
        ("delete_source_use_case", DeleteSourceUseCase),
        ("assign_source_use_case", AssignSourceUseCase),
        ("unassign_source_use_case", UnassignSourceUseCase),
        ("get_cinema_source_use_case", GetCinemaSourceUseCase),
        ("list_registry_sources_use_case", ListRegistrySourcesUseCase),
        ("fetch_screenings_use_case", FetchScreeningsFromSourceQuery),
        ("create_movies_use_case", CreateMissingMoviesCommand),
        ("create_screenings_use_case", CreateScreeningsCommand),
        ("get_cinema_use_case", GetCinemaUseCase),
        ("get_cinema_screenings_query", GetCinemaScreeningsQuery),
        ("get_cinema_movies_use_case", GetCinemaMoviesUseCase),
        ("list_movies_use_case", ListMoviesUseCase),
        ("get_movie_use_case", GetMovieUseCase),
        ("get_movie_screenings_query", GetMovieScreeningsQuery),
        ("search_screenings_query", SearchScreeningsQuery),
        ("get_screening_use_case", GetScreeningUseCase),
    ],
)
async def test_factory_returns_configured_use_cases(
    property_name: str,
    use_case_type: type,
) -> None:
    """Verify every configured use case is available after initialization."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        assert isinstance(getattr(factory, property_name), use_case_type)
        await factory.shutdown()


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_database_health_delegates_to_container() -> None:
    """Verify check_database_health delegates to the container."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()
    mock_database.ping.return_value = True

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        result = await factory.check_database_health()
        assert result is True
        mock_database.ping.assert_awaited_once()
        await factory.shutdown()


@pytest.mark.asyncio
async def test_check_database_health_returns_false_before_init() -> None:
    """Verify check_database_health returns False when not initialized."""
    factory = MarquiseFactory()
    result = await factory.check_database_health()
    assert result is False


# ------------------------------------------------------------------
# Async context manager
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_lifecycle() -> None:
    """Verify async with initializes and shuts down the factory."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        async with MarquiseFactory() as factory:
            assert isinstance(factory.list_cinemas_use_case, ListCinemasUseCase)
            mock_database.connect.assert_awaited_once()

        mock_database.disconnect.assert_awaited_once()


# ------------------------------------------------------------------
# create_factory
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_factory_returns_initialized_factory() -> None:
    """Verify create_factory returns an initialized MarquiseFactory."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = await create_factory()
        assert isinstance(factory, MarquiseFactory)
        assert isinstance(factory.list_cinemas_use_case, ListCinemasUseCase)
        mock_database.connect.assert_awaited_once()
        await factory.shutdown()


# ------------------------------------------------------------------
# create_factory_session
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_factory_session_lifecycle() -> None:
    """Verify create_factory_session manages lifecycle correctly."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        async with create_factory_session() as factory:
            assert isinstance(factory, MarquiseFactory)
            mock_database.connect.assert_awaited_once()

        mock_database.disconnect.assert_awaited_once()
