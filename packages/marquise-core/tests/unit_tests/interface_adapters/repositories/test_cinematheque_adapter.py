"""Tests for CinemathequeAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId
from marquise.interface_adapters.repositories.source_adapters.cinematheque import (
    CinemathequeAdapter,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide the Cinémathèque québécoise cinema."""
    return Cinema(
        id=CinemaId(value="cin-cinematheque"),
        name="Cinémathèque québécoise",
    )


@pytest.fixture
def mock_source() -> AsyncMock:
    """Provide a mocked CinemathequeSource."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_fetch_showtimes_delegates_to_source(
    sample_cinema: Cinema,
    mock_source: AsyncMock,
) -> None:
    """Verify start/end dates pass through untouched (no cinema-name mapping)."""
    start = datetime(2026, 7, 9, tzinfo=UTC)
    end = datetime(2026, 8, 9, tzinfo=UTC)
    mock_source.fetch_showtimes.return_value = [{"movie_title": "A Movie"}]

    adapter = CinemathequeAdapter(mock_source)
    result = await adapter.fetch_showtimes(sample_cinema, start, end)

    assert result == [{"movie_title": "A Movie"}]
    mock_source.fetch_showtimes.assert_awaited_once_with(
        start_date=start,
        end_date=end,
    )
