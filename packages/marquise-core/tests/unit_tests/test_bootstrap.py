"""Tests for MarquiseFactory bootstrap API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from marquise.bootstrap import MarquiseFactory, create_factory, create_factory_session
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.infrastructure.controllers.source_controller import SourceController


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
# Controller properties
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cinema_property_returns_cinema_controller() -> None:
    """Verify cinema property returns a CinemaController after init."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        assert isinstance(factory.cinema, CinemaController)
        await factory.shutdown()


@pytest.mark.asyncio
async def test_source_property_returns_source_controller() -> None:
    """Verify source property returns a SourceController after init."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        assert isinstance(factory.source, SourceController)
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
            assert isinstance(factory.cinema, CinemaController)
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
        assert isinstance(factory.cinema, CinemaController)
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
