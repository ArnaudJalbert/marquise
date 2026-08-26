"""Tests for ImportScreeningsCommand."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand


@pytest.mark.asyncio
async def test_import_normalizes_movie_title_case_before_linking_screenings() -> None:
    """Import links screening when source changes movie-title casing."""
    fetch = create_autospec(FetchScreeningsFromSourceQuery, instance=True)
    fetch.execute = AsyncMock(
        return_value=FetchScreeningsFromSourceQuery.OutputData(
            cinema_id="cin-1",
            cinema_name="Cinema One",
            source_name="cineplex",
            movies=(FetchScreeningsFromSourceQuery.FetchedMovieData(title="Dune"),),
            screenings=(
                FetchScreeningsFromSourceQuery.FetchedScreeningData(
                    movie_title="dune",
                    showtime=datetime(2026, 8, 25, tzinfo=UTC),
                ),
            ),
        )
    )
    movies = create_autospec(CreateMissingMoviesCommand, instance=True)
    movies.execute = AsyncMock(
        return_value=CreateMissingMoviesCommand.OutputData(
            movies=(CreateMissingMoviesCommand.MovieData(title="Dune", id="movie-1"),)
        )
    )
    screenings = create_autospec(CreateScreeningsCommand, instance=True)
    screenings.execute = AsyncMock(
        return_value=CreateScreeningsCommand.OutputData((), 1, 1, 0, 0)
    )

    command = ImportScreeningsCommand(fetch, movies, screenings)
    result = await command.execute(
        ImportScreeningsCommand.InputData(
            cinema_id="cin-1",
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 25),
        )
    )

    assert result.imported_count == 1
    screening_input = screenings.execute.call_args.args[0].screenings[0]
    assert screening_input.movie_id == "movie-1"
