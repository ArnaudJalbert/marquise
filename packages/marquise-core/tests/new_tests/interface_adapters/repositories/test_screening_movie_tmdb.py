from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.domain.value_objects import CinemaId, ScreeningId
from marquise.interface_adapters.repositories.protocols.base import GatewayPage
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningGateway,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


@pytest.fixture
def screening_row() -> dict:
    """A joined screening row includes its movie TMDB metadata."""
    return {
        "id": "scr-1",
        "showtime": datetime(2026, 6, 7, 19, 30),
        "movie__id": "mov-1",
        "movie__title": "Test Movie",
        "movie__tmdb_id": "123",
        "movie__tmdb_rating": 8.2,
        "movie__tmdb_vote_count": 203,
        "cinema__id": "cin-1",
        "cinema__name": "Test Cinema",
    }


@pytest.fixture
def movie_page() -> GatewayPage:
    """A distinct-movie page includes the movie TMDB metadata."""
    return GatewayPage(
        rows=[
            {
                "id": "mov-1",
                "title": "Test Movie",
                "tmdb_id": "123",
                "tmdb_rating": 8.2,
                "tmdb_vote_count": 203,
            }
        ],
        total=1,
    )


@pytest.mark.asyncio
async def test_find_by_id_returns_tmdb_fields_on_screening_movie(
    screening_row: dict,
) -> None:
    """A Screening's Movie keeps its TMDB metadata from the joined row."""
    gateway = create_autospec(ScreeningGateway, instance=True)
    gateway.find_by_id.return_value = screening_row

    result = await SupabaseScreeningRepository(gateway).find_by_id(
        ScreeningId(value="scr-1")
    )

    assert result.movie.tmdb_id == "123"
    assert result.movie.tmdb_rating == 8.2
    assert result.movie.tmdb_vote_count == 203


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema_returns_tmdb_fields(
    movie_page: GatewayPage,
) -> None:
    """Distinct Movies keep their TMDB metadata from the gateway row."""
    gateway = create_autospec(ScreeningGateway, instance=True)
    gateway.find_distinct_movies_by_cinema.return_value = movie_page
    start = datetime(2026, 6, 7, tzinfo=UTC)

    result = await SupabaseScreeningRepository(gateway).find_distinct_movies_by_cinema(
        cinema_id=CinemaId(value="cin-1"), start_date=start, end_date=start
    )

    movie = result.items[0]
    assert movie.tmdb_id == "123"
    assert movie.tmdb_rating == 8.2
    assert movie.tmdb_vote_count == 203
