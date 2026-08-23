"""Tests for DI Container."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from marquise.infrastructure.di.container import Container


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables before each test."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


def test_pool_property_raises_before_initialize() -> None:
    """Verify accessing _pool_property before init raises RuntimeError."""
    container = Container()
    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = container._pool_property  # type: ignore[misc]


@pytest.mark.asyncio
async def test_initialize_and_shutdown() -> None:
    """Verify initialize opens the pool and shutdown closes it."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()

        mock_database.connect.assert_awaited_once()
        assert container._pool is mock_database.pool

        await container.shutdown()
        mock_database.disconnect.assert_awaited_once()
        assert container._database is None
        assert container._pool is None


@pytest.mark.asyncio
async def test_initialize_is_idempotent() -> None:
    """Verify calling initialize twice only creates one pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        await container.initialize()

        mock_database.connect.assert_awaited_once()

        await container.shutdown()


@pytest.mark.asyncio
async def test_shutdown_safe_when_not_initialized() -> None:
    """Verify shutdown does not raise when initialize was never called."""
    container = Container()
    await container.shutdown()


@pytest.mark.asyncio
async def test_cinema_controller_requires_initialize() -> None:
    """Verify cinema_controller raises RuntimeError if pool not initialized."""
    with patch(
        "marquise.infrastructure.di.container.Database",
        return_value=AsyncMock(),
    ):
        container = Container()
        with pytest.raises(RuntimeError, match="Database pool not available"):
            _ = container.cinema_controller


@pytest.mark.asyncio
async def test_delete_cinema_use_case_requires_initialize() -> None:
    """Verify delete_cinema_use_case raises before pool initialization."""
    with patch(
        "marquise.infrastructure.di.container.Database",
        return_value=AsyncMock(),
    ):
        container = Container()
        with pytest.raises(RuntimeError, match="Database pool not available"):
            _ = container.delete_cinema_use_case


@pytest.mark.asyncio
async def test_delete_cinema_use_case_after_initialize() -> None:
    """Verify delete_cinema_use_case uses the initialized database pool."""
    from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        use_case = container.delete_cinema_use_case
        assert isinstance(use_case, DeleteCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool
        await container.shutdown()


@pytest.mark.asyncio
async def test_update_cinema_use_case_requires_initialize() -> None:
    """Verify update_cinema_use_case raises before pool initialization."""
    with patch(
        "marquise.infrastructure.di.container.Database",
        return_value=AsyncMock(),
    ):
        container = Container()
        with pytest.raises(RuntimeError, match="Database pool not available"):
            _ = container.update_cinema_use_case


@pytest.mark.asyncio
async def test_update_cinema_use_case_after_initialize() -> None:
    """Verify update_cinema_use_case uses the initialized database pool."""
    from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        use_case = container.update_cinema_use_case
        assert isinstance(use_case, UpdateCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool
        await container.shutdown()


@pytest.mark.asyncio
async def test_list_cinema_source_assignments_query_requires_initialize() -> None:
    """Verify assignment query raises before pool initialization."""
    with patch(
        "marquise.infrastructure.di.container.Database",
        return_value=AsyncMock(),
    ):
        container = Container()
        with pytest.raises(RuntimeError, match="Database pool not available"):
            _ = container.list_cinema_source_assignments_query


@pytest.mark.asyncio
async def test_list_cinema_source_assignments_query_after_initialize() -> None:
    """Verify assignment query uses initialized database pool."""
    from marquise.application.use_cases.list_cinema_source_assignments import (
        ListCinemaSourceAssignmentsQuery,
    )

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        query = container.list_cinema_source_assignments_query
        assert isinstance(query, ListCinemaSourceAssignmentsQuery)
        assert query._reader._pool is mock_database.pool
        await container.shutdown()


@pytest.mark.asyncio
async def test_get_cinema_use_case_requires_initialize() -> None:
    """Verify get_cinema_use_case raises RuntimeError if pool not initialized."""
    with patch(
        "marquise.infrastructure.di.container.Database",
        return_value=AsyncMock(),
    ):
        container = Container()
        with pytest.raises(RuntimeError, match="Database pool not available"):
            _ = container.get_cinema_use_case


@pytest.mark.asyncio
async def test_get_cinema_use_case_after_initialize() -> None:
    """Verify get_cinema_use_case returns a GetCinemaUseCase after initialize."""
    from marquise.application.use_cases.get_cinema import GetCinemaUseCase

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        use_case = container.get_cinema_use_case
        assert isinstance(use_case, GetCinemaUseCase)
        await container.shutdown()


@pytest.mark.asyncio
async def test_get_movie_use_case_requires_initialize() -> None:
    """Verify get_movie_use_case raises RuntimeError if pool not initialized."""
    with patch(
        "marquise.infrastructure.di.container.Database",
        return_value=AsyncMock(),
    ):
        container = Container()
        with pytest.raises(RuntimeError, match="Database pool not available"):
            _ = container.get_movie_use_case


@pytest.mark.asyncio
async def test_get_movie_use_case_after_initialize() -> None:
    """Verify get_movie_use_case returns a GetMovieUseCase after initialize."""
    from marquise.application.use_cases.get_movie import GetMovieUseCase

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        use_case = container.get_movie_use_case
        assert isinstance(use_case, GetMovieUseCase)
        await container.shutdown()


@pytest.mark.asyncio
async def test_get_cinema_screenings_use_case_after_initialize() -> None:
    """Verify get_cinema_screenings_use_case returns a GetCinemaScreeningsUseCase."""
    from marquise.application.use_cases.get_cinema_screenings import (
        GetCinemaScreeningsUseCase,
    )

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        use_case = container.get_cinema_screenings_use_case
        assert isinstance(use_case, GetCinemaScreeningsUseCase)
        await container.shutdown()


@pytest.mark.asyncio
async def test_search_screenings_use_case_after_initialize() -> None:
    """Verify search_screenings_use_case returns a SearchScreeningsUseCase."""
    from marquise.application.use_cases.search_screenings import (
        SearchScreeningsUseCase,
    )

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        use_case = container.search_screenings_use_case
        assert isinstance(use_case, SearchScreeningsUseCase)
        await container.shutdown()


@pytest.mark.asyncio
async def test_get_screening_use_case_after_initialize() -> None:
    """Verify get_screening_use_case returns a GetScreeningUseCase."""
    from marquise.application.use_cases.get_screening import GetScreeningUseCase

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        use_case = container.get_screening_use_case
        assert isinstance(use_case, GetScreeningUseCase)
        await container.shutdown()


@pytest.mark.asyncio
async def test_cinema_controller_after_initialize() -> None:
    """Verify cinema_controller is available after initialize."""
    from marquise.infrastructure.controllers.cinema_controller import (
        CinemaController,
    )

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        controller = container.cinema_controller
        assert isinstance(controller, CinemaController)
        await container.shutdown()
