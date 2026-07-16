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

# The API returns showtimes up to ~10 days ahead.  The test range must be
# generous enough to cover late Montreal evening shows that become the next
# UTC day after conversion (e.g. a July 23 21:30 EDT show becomes July 24
# 01:30 UTC), but also to include whatever default-window the upstream API
# happens to serve on a given day.
_RANGE_DAYS = 14


@pytest.mark.asyncio
@pytest.mark.parametrize("cinema_name", _CINEMA_SLUGS)
async def test_fetch_showtimes_returns_data(cinema_name: str) -> None:
    """Verify the live cinemacinema.ca API returns showtimes for the given cinema."""
    source = CinemaCinemaSource()
    start = datetime.now(UTC)
    end = start + timedelta(days=_RANGE_DAYS)

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
        # Showtimes should be no older than the previous UTC day (to allow
        # for any late-Montreal-evening shows that crossed midnight UTC)
        # and no further out than the requested end date.
        assert showtime.date() >= start.date() - timedelta(days=1)
        assert showtime.date() <= end.date()


@pytest.mark.asyncio
@pytest.mark.parametrize("cinema_name", _CINEMA_SLUGS)
async def test_fetch_movie_detail_for_a_showtime(cinema_name: str) -> None:
    """Verify movie detail enrichment works for a film currently playing there."""
    source = CinemaCinemaSource()
    start = datetime.now(UTC)
    end = start + timedelta(days=8)

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
