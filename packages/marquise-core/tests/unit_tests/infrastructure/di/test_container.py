"""Tests for DI Container."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from marquise.infrastructure.di.container import Container


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables before each test."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


@pytest.mark.asyncio
async def test_database_initialization_still_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deferring database configuration does not hide initialization errors."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    container = Container()

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        await container.initialize()


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
async def test_get_screening_query_after_initialize() -> None:
    """Verify get_screening_query returns a GetScreeningQuery."""
    from marquise.application.queries.get_screening import GetScreeningQuery

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.container.Database", return_value=mock_database
    ):
        container = Container()
        await container.initialize()
        query = container.get_screening_query
        assert isinstance(query, GetScreeningQuery)
        assert query.screening_reader._gateway._pool is mock_database.pool
        assert query.screening_reader._gateway._schema == "marquise"
        await container.shutdown()
