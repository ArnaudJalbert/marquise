"""Tests for CineStarzAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId
from marquise.interface_adapters.gateways.showtime_source import (
    ShowtimeSource,
)
from marquise.interface_adapters.sources.cinestarz import (
    CineStarzAdapter,
)


@pytest.mark.parametrize(
    ("name", "venue_key"),
    [
        ("Ciné Starz Côte-des-Neiges", "CotedesNeiges"),
        ("Ciné Starz Deluxe Cavendish", "DeluxeCavendish"),
    ],
)
@pytest.mark.asyncio
async def test_fetch_showtimes_maps_cinema_to_venue_key(
    name: str, venue_key: str
) -> None:
    """Exact Cine Starz cinema names resolve to their venue keys."""
    source = create_autospec(ShowtimeSource, instance=True)
    source.fetch_showtimes.return_value = []
    cinema = Cinema(id=CinemaId(value="cin-cinestarz"), name=name)
    start = datetime(2026, 8, 26, tzinfo=UTC)
    end = datetime(2026, 8, 27, tzinfo=UTC)

    result = await CineStarzAdapter(source).fetch_showtimes(cinema, start, end)

    assert result == []
    source.fetch_showtimes.assert_awaited_once_with(
        venue_key=venue_key, start_date=start, end_date=end
    )


@pytest.mark.asyncio
async def test_fetch_showtimes_rejects_unknown_cinema() -> None:
    """Unmapped cinema does not call source."""
    source = create_autospec(ShowtimeSource, instance=True)
    cinema = Cinema(id=CinemaId(value="cin-unknown"), name="Unknown Cinema")

    with pytest.raises(ValueError, match="No Cine Starz venue mapping"):
        await CineStarzAdapter(source).fetch_showtimes(
            cinema, datetime(2026, 8, 26, tzinfo=UTC), datetime(2026, 8, 27, tzinfo=UTC)
        )

    source.fetch_showtimes.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_movie_detail_delegates_to_source() -> None:
    """Movie identifier passes through unchanged."""
    source = create_autospec(ShowtimeSource, instance=True)
    source.fetch_movie_detail.return_value = {"description": "Story"}

    result = await CineStarzAdapter(source).fetch_movie_detail(
        "https://cinestarz.ca/movie/CotedesNeiges/MOVIE"
    )

    assert result == {"description": "Story"}
    source.fetch_movie_detail.assert_awaited_once_with(
        identifier="https://cinestarz.ca/movie/CotedesNeiges/MOVIE"
    )
