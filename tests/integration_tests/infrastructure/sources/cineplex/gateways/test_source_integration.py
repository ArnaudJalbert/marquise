"""Integration tests for CineplexSource against the real Cineplex API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from marquise.infrastructure.sources.cineplex.gateways.source import CineplexSource

QUARTIER_LATIN_LOCATION_ID = 9172  # Cinéma Cineplex Odeon Quartier Latin
ROYALMOUNT_LOCATION_ID = 9121  # Cinéma Cineplex Royalmount

_LOCATION_IDS = [
    pytest.param(QUARTIER_LATIN_LOCATION_ID, id="quartier-latin"),
    pytest.param(ROYALMOUNT_LOCATION_ID, id="royalmount"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("location_id", _LOCATION_IDS)
async def test_fetch_showtimes_returns_data(location_id: int) -> None:
    """Verify the live Cineplex API returns showtimes for the given cinema."""
    source = CineplexSource()
    start = datetime.now(UTC)
    end = start + timedelta(days=7)

    results = await source.fetch_showtimes(
        location_id=location_id,
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
        assert entry["ticket_url"]
        showtime = datetime.fromisoformat(entry["showtime"])
        assert start <= showtime <= end


@pytest.mark.asyncio
@pytest.mark.parametrize("location_id", _LOCATION_IDS)
async def test_fetch_movie_detail_for_a_showtime(location_id: int) -> None:
    """Verify movie detail enrichment works for a film currently playing there."""
    source = CineplexSource()
    start = datetime.now(UTC)
    end = start + timedelta(days=7)

    showtimes = await source.fetch_showtimes(
        location_id=location_id,
        start_date=start,
        end_date=end,
    )
    assert showtimes, "expected at least one showtime to test detail lookup"

    detail = await source.fetch_movie_detail(showtimes[0]["identifier"])

    assert detail is not None
    assert "description" in detail
    assert "genres" in detail
