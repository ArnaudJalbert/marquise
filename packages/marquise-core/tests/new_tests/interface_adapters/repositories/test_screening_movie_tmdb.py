from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime
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
        "movie__release_year": 2026,
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


@pytest.fixture
def incoming_screening() -> Screening:
    """An incoming screening identifies the candidate to read."""
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=Movie(id=MovieId(value="mov-1"), title="Test Movie"),
        cinema=Cinema(id=CinemaId(value="cin-1"), name="Test Cinema"),
        showtime=Showtime(value=datetime(2026, 6, 7, 19, 30, tzinfo=UTC)),
    )


@pytest.mark.asyncio
async def test_read_import_candidates_preserves_movie_release_year(
    screening_row: dict, incoming_screening: Screening
) -> None:
    """Candidate reads preserve the Movie release year."""
    gateway = create_autospec(ScreeningGateway, instance=True)
    gateway.read_import_candidates.return_value = [screening_row]

    result = await SupabaseScreeningRepository(gateway).read_import_candidates(
        incoming_screening
    )

    assert result[0].movie.release_year == 2026


@pytest.mark.asyncio
async def test_read_import_candidates_returns_tmdb_fields_on_screening_movie(
    screening_row: dict, incoming_screening: Screening
) -> None:
    """A Screening's Movie keeps its TMDB metadata from the joined row."""
    gateway = create_autospec(ScreeningGateway, instance=True)
    gateway.read_import_candidates.return_value = [screening_row]

    result = await SupabaseScreeningRepository(gateway).read_import_candidates(
        incoming_screening
    )

    assert len(result) == 1
    assert result[0].movie.tmdb_id == "123"
    assert result[0].movie.tmdb_rating == 8.2
    assert result[0].movie.tmdb_vote_count == 203


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
