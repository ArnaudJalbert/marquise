"""Unit tests for SupabaseScreeningReader."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from marquise.application.readers import ScreeningSummary
from marquise.interface_adapters.readers.screening_reader import (
    SupabaseScreeningReader,
)


def _pool(connection: AsyncMock) -> MagicMock:
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


def _row() -> dict:
    return {
        "id": "scr-1",
        "movie_id": "mov-1",
        "movie_title": "The Odyssey",
        "cinema_id": "cin-1",
        "cinema_name": "Cinema One",
        "showtime": datetime(2026, 6, 27, 19, 30),
        "ticket_url": None,
        "room": None,
        "language": "V.O.",
    }


@pytest.mark.asyncio
async def test_search_maps_projection_and_filters() -> None:
    """Reader maps selected fields and parameterizes every filter."""
    connection = AsyncMock()
    connection.fetch.return_value = [{**_row(), "__total": 1}]
    reader = SupabaseScreeningReader(_pool(connection))
    start = datetime(2026, 6, 27, tzinfo=UTC)
    end = datetime(2026, 6, 28, tzinfo=UTC)

    result = await reader.search(
        movie_id="mov-1",
        movie_title="Odyssey",
        cinema_id="cin-1",
        start_date=start,
        end_date=end,
        language="V.O.",
        limit=5,
        offset=10,
    )

    assert result.items == [
        ScreeningSummary(
            id="scr-1",
            movie_id="mov-1",
            movie_title="The Odyssey",
            cinema_id="cin-1",
            cinema_name="Cinema One",
            showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
            language="V.O.",
        )
    ]
    assert result.total == 1
    connection.fetch.assert_awaited_once_with(
        ANY,
        "mov-1",
        "%Odyssey%",
        "cin-1",
        datetime(2026, 6, 27),
        datetime(2026, 6, 28),
        "V.O.",
        5,
        10,
    )


@pytest.mark.asyncio
async def test_search_without_limit_uses_returned_row_count() -> None:
    """Unpaginated search reports total from returned rows."""
    connection = AsyncMock()
    connection.fetch.return_value = [_row()]

    result = await SupabaseScreeningReader(_pool(connection)).search()

    assert len(result.items) == 1
    assert result.total == 1
    connection.fetchval.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_empty_page_fetches_true_total() -> None:
    """An offset past results falls back to a count query."""
    connection = AsyncMock()
    connection.fetch.return_value = []
    connection.fetchval.return_value = 3

    result = await SupabaseScreeningReader(_pool(connection)).search(
        movie_title="Odyssey", limit=5, offset=10
    )

    assert result.items == []
    assert result.total == 3
    connection.fetchval.assert_awaited_once_with(ANY, "%Odyssey%")
