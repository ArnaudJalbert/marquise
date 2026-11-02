"""Tests for ImportScreeningsCommand."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
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


@pytest.mark.asyncio
async def test_source_identifiers_keep_same_title_screenings_distinct() -> None:
    """Two source films with the same title retain their own screening links."""
    fetch = create_autospec(FetchScreeningsFromSourceQuery, instance=True)
    day = datetime(2026, 10, 31, tzinfo=UTC)
    fetch.execute.return_value = FetchScreeningsFromSourceQuery.OutputData(
        cinema_id="cin-1",
        cinema_name="Cinema",
        source_name="source",
        movies=(
            FetchScreeningsFromSourceQuery.FetchedMovieData(
                title="Same", identifier="one"
            ),
            FetchScreeningsFromSourceQuery.FetchedMovieData(
                title="Same", identifier="two"
            ),
        ),
        screenings=(
            FetchScreeningsFromSourceQuery.FetchedScreeningData(
                movie_title="Same", showtime=day, identifier="one"
            ),
            FetchScreeningsFromSourceQuery.FetchedScreeningData(
                movie_title="Same", showtime=day, identifier="two"
            ),
        ),
    )
    movies = create_autospec(CreateMissingMoviesCommand, instance=True)
    movies.execute.return_value = CreateMissingMoviesCommand.OutputData(
        movies=(
            CreateMissingMoviesCommand.MovieData("Same", "movie-1", "one"),
            CreateMissingMoviesCommand.MovieData("Same", "movie-2", "two"),
        )
    )
    screenings = create_autospec(CreateScreeningsCommand, instance=True)
    screenings.execute.return_value = CreateScreeningsCommand.OutputData((), 2, 2, 0, 0)
    command = ImportScreeningsCommand(fetch, movies, screenings)
    await command.execute(
        command.InputData(cinema_id="cin-1", start_date=day.date(), end_date=day.date())
    )
    assert [
        item.movie_id for item in screenings.execute.await_args.args[0].screenings
    ] == ["movie-1", "movie-2"]


@pytest.mark.asyncio
async def test_import_maps_create_results_into_its_own_screening_data() -> None:
    """Import returns its own per-screening type with the same values and counts."""
    fetch = create_autospec(FetchScreeningsFromSourceQuery, instance=True)
    fetch.execute.return_value = FetchScreeningsFromSourceQuery.OutputData(
        cinema_id="cin-1",
        cinema_name="Cinema",
        source_name="source",
        movies=(),
        screenings=(),
    )
    movies = create_autospec(CreateMissingMoviesCommand, instance=True)
    movies.execute.return_value = CreateMissingMoviesCommand.OutputData(movies=())
    screenings = create_autospec(CreateScreeningsCommand, instance=True)
    screenings.execute.return_value = CreateScreeningsCommand.OutputData(
        screenings=(
            CreateScreeningsCommand.ScreeningData("Dune", "2026-08-25T19:00", True),
            CreateScreeningsCommand.ScreeningData(
                "Alien", "2026-08-26T19:00", False, rescheduled=True
            ),
        ),
        total_count=2,
        imported_count=1,
        updated_count=0,
        skipped_count=3,
        rescheduled_count=1,
    )
    command = ImportScreeningsCommand(fetch, movies, screenings)

    result = await command.execute(
        command.InputData(
            cinema_id="cin-1",
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 26),
        )
    )

    assert result.screenings == (
        ImportScreeningsCommand.ScreeningData("Dune", "2026-08-25T19:00", True),
        ImportScreeningsCommand.ScreeningData(
            "Alien", "2026-08-26T19:00", False, rescheduled=True
        ),
    )
    assert (
        result.total_count,
        result.imported_count,
        result.updated_count,
        result.skipped_count,
        result.rescheduled_count,
    ) == (2, 1, 0, 3, 1)
