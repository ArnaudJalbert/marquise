"""Integration tests for CinemaCinemaSource against the real cinemacinema.ca API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from marquise.infrastructure.sources.cinemacinema.gateways.source import (
    CinemaCinemaSource,
)

_CINEMA_SLUGS = [
    pytest.param("du-musee", id="du-musee"),
    pytest.param("du-parc", id="du-parc"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("cinema_name", _CINEMA_SLUGS)
async def test_fetch_showtimes_returns_data(cinema_name: str) -> None:
    """Verify the live cinemacinema.ca API returns showtimes for the given cinema."""
    source = CinemaCinemaSource()
    start = datetime.now(UTC)
    end = start + timedelta(days=7)

    results = await source.fetch_showtimes(
        cinema_name=cinema_name,
        start_date=start,
        end_date=end,
    )

    assert isinstance(results, list)
    assert len(results) > 0
    for entry in results:
        assert entry["movie_title"]
        assert entry["showtime"]
        assert entry["identifier"]
        assert entry["external_id"]
        showtime = datetime.fromisoformat(entry["showtime"])
        assert start.date() <= showtime.date() <= end.date()


@pytest.mark.asyncio
@pytest.mark.parametrize("cinema_name", _CINEMA_SLUGS)
async def test_fetch_movie_detail_for_a_showtime(cinema_name: str) -> None:
    """Verify movie detail enrichment works for a film currently playing there."""
    source = CinemaCinemaSource()
    start = datetime.now(UTC)
    end = start + timedelta(days=7)

    showtimes = await source.fetch_showtimes(
        cinema_name=cinema_name,
        start_date=start,
        end_date=end,
    )
    assert showtimes, "expected at least one showtime to test detail lookup"

    detail = await source.fetch_movie_detail(showtimes[0]["identifier"])

    assert detail is not None
    assert "description" in detail
    assert "genres" in detail
