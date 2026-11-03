"""Unit coverage for the movie-card read adapter without external I/O."""

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.interface_adapters.readers.screening_movie_reader import (
    ScreeningMovieReadGateway,
    SupabaseScreeningMovieReader,
)
from marquise.interface_adapters.repositories.protocols.base import GatewayPage


@pytest.mark.asyncio
async def test_movie_projection_maps_metadata_previews_and_empty_pages() -> None:
    """The injected gateway supplies all data, including missing optional fields."""
    gateway = create_autospec(ScreeningMovieReadGateway, instance=True)
    gateway.search.return_value = GatewayPage(
        rows=[
            {
                "id": "m1",
                "title": "Movie",
                "release_year": None,
                "directors": None,
                "description": None,
                "poster_url": None,
                "duration_minutes": None,
                "tmdb_rating": 8.1,
                "tmdb_vote_count": 1234,
                "screenings": [
                    {
                        "id": "s1",
                        "movie_id": "m1",
                        "movie_title": "Movie",
                        "cinema_id": "c1",
                        "cinema_name": "Cinema",
                        "showtime": datetime(2026, 11, 1, 5, 30),
                        "language": "VO",
                    }
                ],
            }
        ],
        total=25,
    )
    now = datetime(2026, 11, 1, 4, tzinfo=UTC)
    reader = SupabaseScreeningMovieReader(gateway)
    result = await reader.search(now, now, now, 2)
    gateway.search.assert_awaited_once_with(now, now, now, 2, None, (), (), (), ())
    assert result.total == 25
    movie = result.items[0]
    assert movie.directors is None and movie.poster_url is None
    assert movie.tmdb_rating == 8.1 and movie.tmdb_vote_count == 1234
    assert movie.screenings[0].showtime == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
    assert movie.screenings[0].language == "VO"
    assert movie.screenings[0].ticket_url is None
    gateway.search.return_value = GatewayPage(rows=[], total=25)
    result = await reader.search(now, now, now, 3)
    assert result.total == 25 and result.items == []
