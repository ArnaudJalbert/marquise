"""Tests for the create_factory and create_factory_session bootstrap API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.bootstrap import create_factory, create_factory_session
from marquise.infrastructure.di.factory import MarquiseFactory


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables before each test."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


# ------------------------------------------------------------------
# create_factory
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_factory_returns_initialized_factory() -> None:
    """Verify create_factory returns an initialized MarquiseFactory."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
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
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        async with create_factory_session() as factory:
            assert isinstance(factory, MarquiseFactory)
            mock_database.connect.assert_awaited_once()

        mock_database.disconnect.assert_awaited_once()
