"""Tests for CineplexAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId
from marquise.interface_adapters.repositories.source_adapters.cineplex import (
    CineplexAdapter,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide a known Cineplex cinema."""
    return Cinema(
        id=CinemaId(value="cin-9406"),
        name="Cinéma Banque Scotia Montréal",
    )


@pytest.fixture
def unknown_cinema() -> Cinema:
    """Provide a cinema not in the Cineplex mapping."""
    return Cinema(
        id=CinemaId(value="cin-unknown"),
        name="Unknown Cinema",
    )


@pytest.fixture
def mock_source() -> AsyncMock:
    """Provide a mocked CineplexSource."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_fetch_showtimes_maps_cinema_to_location_id(
    sample_cinema: Cinema,
    mock_source: AsyncMock,
) -> None:
    """Verify correct location_id is passed to the source."""
    start = datetime(2026, 6, 7, tzinfo=UTC)
    end = datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC)
    mock_source.fetch_showtimes.return_value = []

    adapter = CineplexAdapter(mock_source)
    result = await adapter.fetch_showtimes(sample_cinema, start, end)

    assert result == []
    mock_source.fetch_showtimes.assert_awaited_once_with(
        location_id=9406,
        start_date=start,
        end_date=end,
    )


@pytest.mark.asyncio
async def test_fetch_showtimes_raises_for_unknown_cinema(
    unknown_cinema: Cinema,
    mock_source: AsyncMock,
) -> None:
    """Verify ValueError for unmapped cinema."""
    start = datetime(2026, 6, 7, tzinfo=UTC)
    end = datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC)

    adapter = CineplexAdapter(mock_source)
    with pytest.raises(ValueError, match="No Cineplex location ID mapping"):
        await adapter.fetch_showtimes(unknown_cinema, start, end)

    mock_source.fetch_showtimes.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_movie_detail_delegates_to_source(
    mock_source: AsyncMock,
) -> None:
    """Verify fetch_movie_detail passes the slug to the source."""
    mock_source.fetch_movie_detail.return_value = {"description": "A movie"}

    adapter = CineplexAdapter(mock_source)
    result = await adapter.fetch_movie_detail("the-odyssey")

    assert result == {"description": "A movie"}
    mock_source.fetch_movie_detail.assert_awaited_once_with(slug="the-odyssey")


@pytest.mark.asyncio
async def test_fetch_movie_detail_returns_none(
    mock_source: AsyncMock,
) -> None:
    """Verify None when source returns None."""
    mock_source.fetch_movie_detail.return_value = None

    adapter = CineplexAdapter(mock_source)
    result = await adapter.fetch_movie_detail("non-existent")

    assert result is None
