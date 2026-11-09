"""Import a translated screening using a real database and a known TMDB movie."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import asyncpg
import pytest

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
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
from support.movie_import import (
    autospec_use_case,
    build_match,
    build_matcher,
    import_command,
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

    fetched = autospec_use_case(FetchScreeningsFromSourceQuery)
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
    matcher = build_matcher(build_match("777"))
    command = import_command(
        fetched, movies, CreateScreeningsCommand(screenings), matcher
    )

    result = await command.execute(
        command.InputData("test-cinema", date(2026, 10, 30), date(2026, 10, 30))
    )

    assert result.imported_count == 1
    request = matcher.execute.await_args.args[0].movies[0]
    assert (request.title, request.release_year) == ("Film traduit", 2025)
    saved_screenings = await screenings.search()
    assert saved_screenings.total == 1
    assert saved_screenings.items[0].movie.id == original.id
    assert await movies.find_by_tmdb_id("777") == original
    async with db_pool.acquire() as conn:
        assert await conn.fetchval(f'SELECT count(*) FROM "{TEST_SCHEMA}".movies') == 1
