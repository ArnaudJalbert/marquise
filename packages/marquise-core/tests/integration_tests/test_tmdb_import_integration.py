"""Import a translated screening using a real database and a known TMDB movie."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, create_autospec

import asyncpg
import pytest

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories.tmdb_search import TmdbCandidate, TmdbSearch
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import SupabaseScreeningGateway
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)

TEST_SCHEMA = "marquise-test"


@pytest.mark.asyncio
async def test_import_links_translated_screening_to_known_movie(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """A TMDB match reuses a persisted movie and keeps its details unchanged."""
    movies = SupabaseMovieRepository(movie_gateway)
    screenings = SupabaseScreeningRepository(screening_gateway)
    original = Movie(
        id=MovieId("known-movie"),
        title="Original Film",
        release_year=2025,
        poster_url="original-poster",
        tmdb_id="777",
    )
    await movies.save(original)
    async with db_pool.acquire() as conn:
        await conn.execute(
            f'INSERT INTO "{TEST_SCHEMA}".cinemas (id, name) VALUES ($1, $2)',
            "test-cinema",
            "Test Cinema",
        )

    fetched = create_autospec(FetchScreeningsFromSourceQuery, instance=True)
    fetched.execute = AsyncMock(
        return_value=FetchScreeningsFromSourceQuery.OutputData(
            cinema_id="test-cinema",
            cinema_name="Test Cinema",
            source_name="test-source",
            movies=(
                FetchScreeningsFromSourceQuery.FetchedMovieData(
                    title="Film traduit", release_year=2025
                ),
            ),
            screenings=(
                FetchScreeningsFromSourceQuery.FetchedScreeningData(
                    movie_title="Film traduit",
                    showtime=datetime(2026, 10, 30, 19, tzinfo=UTC),
                ),
            ),
        )
    )
    tmdb = create_autospec(TmdbSearch, instance=True)
    tmdb.search.return_value = [
        TmdbCandidate(id="777", title="Original Film", release_year=2025)
    ]
    command = ImportScreeningsCommand(
        fetched,
        CreateMissingMoviesCommand(movies, tmdb),
        CreateScreeningsCommand(screenings),
    )

    result = await command.execute(
        command.InputData("test-cinema", date(2026, 10, 30), date(2026, 10, 30))
    )

    assert result.imported_count == 1
    tmdb.search.assert_awaited_once_with("Film traduit", 2025)
    saved_screenings = await screenings.search()
    assert saved_screenings.total == 1
    assert saved_screenings.items[0].movie.id == original.id
    assert await movies.find_by_tmdb_id("777") == original
    async with db_pool.acquire() as conn:
        assert await conn.fetchval(f'SELECT count(*) FROM "{TEST_SCHEMA}".movies') == 1
