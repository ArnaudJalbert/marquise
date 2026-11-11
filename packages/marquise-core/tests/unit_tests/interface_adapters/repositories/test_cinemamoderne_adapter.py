"""Tests for CinemaModerneAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId
from marquise.interface_adapters.repositories.source_adapters.cinemamoderne import (
    CinemaModerneAdapter,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide the Cinéma Moderne cinema."""
    return Cinema(
        id=CinemaId(value="cin-cinemamoderne"),
        name="Cinéma Moderne",
    )


@pytest.fixture
def mock_source() -> AsyncMock:
    """Provide a mocked CinemaModerneSource."""
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

    adapter = CinemaModerneAdapter(mock_source)
    result = await adapter.fetch_showtimes(sample_cinema, start, end)

    assert result == [{"movie_title": "A Movie"}]
    mock_source.fetch_showtimes.assert_awaited_once_with(
        start_date=start,
        end_date=end,
    )


@pytest.mark.asyncio
async def test_fetch_movie_detail_delegates_to_source(
    mock_source: AsyncMock,
) -> None:
    """Verify the identifier passes straight through to the source."""
    identifier = "https://www.cinemamoderne.com/films/details/kairos/"
    mock_source.fetch_movie_detail.return_value = {"description": "A film"}

    adapter = CinemaModerneAdapter(mock_source)
    result = await adapter.fetch_movie_detail(identifier)

    assert result == {"description": "A film"}
    mock_source.fetch_movie_detail.assert_awaited_once_with(identifier=identifier)
