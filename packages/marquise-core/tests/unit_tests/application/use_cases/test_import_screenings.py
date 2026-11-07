"""Tests for ImportScreeningsCommand, the import coordinator."""

from datetime import UTC, date, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions.movie import MovieMetadataUnavailableError
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from support.movie_import import (
    autospec_use_case,
    build_match,
    build_matcher,
    build_unchanged_enricher,
    import_command,
)

DAY = datetime(2026, 10, 31, tzinfo=UTC)


def _fetch(
    movies: tuple[FetchScreeningsFromSourceQuery.FetchedMovieData, ...] = (),
    screenings: tuple[FetchScreeningsFromSourceQuery.FetchedScreeningData, ...] = (),
) -> Mock:
    fetch = autospec_use_case(FetchScreeningsFromSourceQuery)
    fetch.execute.return_value = FetchScreeningsFromSourceQuery.OutputData(
        cinema_id="cin-1",
        cinema_name="Cinema",
        source_name="source",
        movies=movies,
        screenings=screenings,
    )
    return fetch


def _movies() -> Mock:
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_tmdb_id.return_value = None
    movies.find_by_titles.return_value = []
    movies.create_or_reuse.side_effect = lambda movie: movie
    return movies


def _create_screenings(
    output: CreateScreeningsCommand.OutputData | None = None,
) -> Mock:
    screenings = autospec_use_case(CreateScreeningsCommand)
    screenings.execute.return_value = output or CreateScreeningsCommand.OutputData(
        (), 1, 1, 0, 0
    )
    return screenings


@pytest.mark.asyncio
async def test_import_normalizes_movie_title_case_before_linking_screenings() -> None:
    """Import links screening when source changes movie-title casing."""
    fetch = _fetch(
        (FetchScreeningsFromSourceQuery.FetchedMovieData(title="Dune"),),
        (
            FetchScreeningsFromSourceQuery.FetchedScreeningData(
                movie_title="dune", showtime=DAY
            ),
        ),
    )
    movies = _movies()
    screenings = _create_screenings()
    command = import_command(fetch, movies, screenings)

    result = await command.execute(
        command.InputData("cin-1", date(2026, 10, 31), date(2026, 10, 31))
    )

    assert result.imported_count == 1
    saved_movie = movies.create_or_reuse.await_args.args[0]
    assert screenings.execute.await_args.args[0].screenings[0].movie_id == (
        saved_movie.id.value
    )


@pytest.mark.asyncio
async def test_source_identifiers_keep_same_title_screenings_distinct() -> None:
    """Two source films with the same title retain their own screening links."""
    fetch = _fetch(
        (
            FetchScreeningsFromSourceQuery.FetchedMovieData(
                title="Same", identifier="one"
            ),
            FetchScreeningsFromSourceQuery.FetchedMovieData(
                title="Same", identifier="two"
            ),
        ),
        (
            FetchScreeningsFromSourceQuery.FetchedScreeningData(
                "Same", DAY, identifier="one"
            ),
            FetchScreeningsFromSourceQuery.FetchedScreeningData(
                "Same", DAY, identifier="two"
            ),
        ),
    )
    movies = _movies()
    movies.find_by_tmdb_id.side_effect = lambda tmdb_id: Movie(
        id=MovieId(value=f"movie-{tmdb_id}"), title="Same", tmdb_id=tmdb_id
    )
    screenings = _create_screenings()
    matcher = build_matcher(build_match("1"), build_match("2"))
    command = import_command(fetch, movies, screenings, matcher)

    await command.execute(command.InputData("cin-1", DAY.date(), DAY.date()))

    assert [
        item.movie_id for item in screenings.execute.await_args.args[0].screenings
    ] == ["movie-1", "movie-2"]


@pytest.mark.asyncio
async def test_import_maps_create_results_into_its_own_screening_data() -> None:
    """Import returns its own per-screening type with the same values and counts."""
    screenings = _create_screenings(
        CreateScreeningsCommand.OutputData(
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
    )
    command = import_command(_fetch(), _movies(), screenings)

    result = await command.execute(command.InputData("cin-1", DAY.date(), DAY.date()))

    assert result.screenings == (
        command.ScreeningData("Dune", "2026-08-25T19:00", True),
        command.ScreeningData("Alien", "2026-08-26T19:00", False, rescheduled=True),
    )
    assert (
        result.total_count,
        result.imported_count,
        result.updated_count,
        result.skipped_count,
        result.rescheduled_count,
    ) == (2, 1, 0, 3, 1)


@pytest.mark.asyncio
async def test_enrichment_outage_fails_the_import_after_saving_screenings() -> None:
    """An outage while enriching can't lose screenings that were already saved."""
    screenings = _create_screenings()
    enricher = build_unchanged_enricher()
    enricher.execute.side_effect = MovieMetadataUnavailableError("offline")
    fetch = _fetch(
        (FetchScreeningsFromSourceQuery.FetchedMovieData(title="Dune"),),
        (
            FetchScreeningsFromSourceQuery.FetchedScreeningData(
                movie_title="Dune", showtime=DAY
            ),
        ),
    )
    command = import_command(fetch, _movies(), screenings, enricher=enricher)

    with pytest.raises(MovieMetadataUnavailableError):
        await command.execute(command.InputData("cin-1", DAY.date(), DAY.date()))

    screenings.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_stored_and_created_movies_are_all_enriched_with_their_identity() -> None:
    """Enrichment gets every movie, including the identity matching confirmed."""
    fetch = _fetch(
        (
            FetchScreeningsFromSourceQuery.FetchedMovieData(title="Matched"),
            FetchScreeningsFromSourceQuery.FetchedMovieData(title="Unmatched"),
        ),
        (
            FetchScreeningsFromSourceQuery.FetchedScreeningData("Matched", DAY),
            FetchScreeningsFromSourceQuery.FetchedScreeningData("Unmatched", DAY),
        ),
    )
    enricher = build_unchanged_enricher()
    command = import_command(
        fetch,
        _movies(),
        _create_screenings(),
        build_matcher(build_match("7")),
        enricher,
    )

    await command.execute(command.InputData("cin-1", DAY.date(), DAY.date()))

    movies = enricher.execute.await_args.args[0].movies
    assert sorted(str(movie.tmdb_id) for movie in movies) == ["7", "None"]


@pytest.mark.asyncio
async def test_a_failed_save_skips_enrichment() -> None:
    """Failures propagate, so nothing runs after the failed step."""
    screenings = _create_screenings()
    screenings.execute.side_effect = ConnectionError("offline")
    enricher = build_unchanged_enricher()
    command = import_command(_fetch(), _movies(), screenings, enricher=enricher)

    with pytest.raises(ConnectionError):
        await command.execute(command.InputData("cin-1", DAY.date(), DAY.date()))

    enricher.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "fields",
    [
        {"cinema_id": 1, "start_date": DAY.date(), "end_date": DAY.date()},
        {"cinema_id": "cin-1", "start_date": "2026", "end_date": DAY.date()},
        {"cinema_id": "cin-1", "start_date": DAY.date(), "end_date": "2026"},
    ],
)
def test_input_rejects_wrong_types(fields: dict) -> None:
    """Input is the one place types are checked."""
    with pytest.raises(TypeError):
        ImportScreeningsCommand.InputData(**fields)
