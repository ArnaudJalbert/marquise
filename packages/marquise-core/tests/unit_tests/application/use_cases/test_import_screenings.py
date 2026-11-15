"""Tests for ImportScreeningsCommand, the import coordinator."""

from datetime import UTC, date, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions import MetadataUnavailableError
from marquise.application.exceptions.movie import MovieNotLinkedError
from marquise.application.metadata import MetadataBatch, MetadataRepository
from marquise.application.movie_workflows import (
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
)
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
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
FetchedMovie = FetchScreeningsFromSourceQuery.FetchedMovieData
FetchedScreening = FetchScreeningsFromSourceQuery.FetchedScreeningData


def _fetched(
    movies: tuple[FetchedMovie, ...], screenings: tuple[FetchedScreening, ...]
) -> FetchScreeningsFromSourceQuery.OutputData:
    return FetchScreeningsFromSourceQuery.OutputData(
        cinema_id="cin-1",
        cinema_name="Cinema",
        source_name="source",
        movies=movies,
        screenings=screenings,
    )


@pytest.fixture
def fetch_screenings() -> Mock:
    """A source with one movie and one screening of it."""
    fetch_screenings = autospec_use_case(FetchScreeningsFromSourceQuery)
    fetch_screenings.execute.return_value = _fetched(
        (FetchedMovie(title="Dune"),),
        (FetchedScreening(movie_title="dune", showtime=DAY),),
    )
    return fetch_screenings


@pytest.fixture
def movie_repository() -> Mock:
    """A repository with no stored movies."""
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.find_by_tmdb_id.return_value = None
    movie_repository.find_by_titles.return_value = []
    movie_repository.create_or_reuse.side_effect = lambda movie: movie
    return movie_repository


@pytest.fixture
def create_screenings() -> Mock:
    """A screenings command reporting one import."""
    create_screenings = autospec_use_case(CreateScreeningsCommand)
    create_screenings.execute.return_value = CreateScreeningsCommand.OutputData(
        (), 1, 1, 0, 0
    )
    return create_screenings


@pytest.fixture
def enricher() -> Mock:
    """An enricher that leaves every movie as it is."""
    return build_unchanged_enricher()


@pytest.fixture
def matcher() -> Mock:
    """A matcher that never matches."""
    return build_matcher()


@pytest.fixture
def command(
    fetch_screenings: Mock,
    movie_repository: Mock,
    create_screenings: Mock,
    matcher: Mock,
    enricher: Mock,
) -> ImportScreeningsCommand:
    """The real coordinator, with real movie use cases and mocked edges."""
    return import_command(
        fetch_screenings, movie_repository, create_screenings, matcher, enricher
    )


def _input() -> ImportScreeningsCommand.InputData:
    return ImportScreeningsCommand.InputData("cin-1", DAY.date(), DAY.date())


@pytest.mark.asyncio
async def test_created_movie_is_found_again_and_linked(
    command: ImportScreeningsCommand,
    movie_repository: Mock,
    create_screenings: Mock,
) -> None:
    """A new movie is looked up again, and its screening links through casing."""
    result = await command.execute(_input())

    assert result.imported_count == 1
    saved_movie = movie_repository.create_or_reuse.await_args.args[0]
    screening = create_screenings.execute.await_args.args[0].screenings[0]
    assert screening.movie_id == saved_movie.id.value
    assert movie_repository.find_by_titles.await_count == 2


@pytest.mark.asyncio
async def test_movie_missing_after_creation_stops_before_screenings(
    command: ImportScreeningsCommand,
    movie_repository: Mock,
    create_screenings: Mock,
) -> None:
    """A screening is never saved without its movie."""
    movie_repository.find_by_titles.side_effect = lambda terms: []
    movie_repository.create_or_reuse.side_effect = lambda movie: Movie(
        id=MovieId(value="elsewhere"), title="Something Else Entirely"
    )

    with pytest.raises(MovieNotLinkedError):
        await command.execute(_input())

    create_screenings.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_identifiers_keep_same_title_screenings_distinct(
    fetch_screenings: Mock,
    movie_repository: Mock,
    create_screenings: Mock,
    enricher: Mock,
) -> None:
    """Two source films with the same title retain their own screening links."""
    fetch_screenings.execute.return_value = _fetched(
        (
            FetchedMovie(title="Same", identifier="one"),
            FetchedMovie(title="Same", identifier="two"),
        ),
        (
            FetchedScreening("Same", DAY, identifier="one"),
            FetchedScreening("Same", DAY, identifier="two"),
        ),
    )
    movie_repository.find_by_tmdb_id.side_effect = lambda tmdb_id: Movie(
        id=MovieId(value=f"movie-{tmdb_id}"), title="Same", tmdb_id=tmdb_id
    )
    command = import_command(
        fetch_screenings,
        movie_repository,
        create_screenings,
        build_matcher(build_match("1"), build_match("2")),
        enricher,
    )

    await command.execute(_input())

    assert [
        item.movie_id
        for item in create_screenings.execute.await_args.args[0].screenings
    ] == ["movie-1", "movie-2"]


@pytest.mark.asyncio
async def test_import_maps_create_results_into_its_own_screening_data(
    fetch_screenings: Mock, command: ImportScreeningsCommand, create_screenings: Mock
) -> None:
    """Import returns its own per-screening type with the same values and counts."""
    fetch_screenings.execute.return_value = _fetched((), ())
    create_screenings.execute.return_value = CreateScreeningsCommand.OutputData(
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

    result = await command.execute(_input())

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
async def test_movies_left_not_enriched_do_not_fail_the_import(
    command: ImportScreeningsCommand, create_screenings: Mock, enricher: Mock
) -> None:
    """A movie enrichment could not finish is left as it is; the import goes on."""
    enricher.execute.return_value = EnrichMoviesUseCase.OutputData((), ("movie-1",))

    result = await command.execute(_input())

    create_screenings.execute.assert_awaited_once()
    enricher.execute.assert_awaited_once()
    assert result.cinema_id == _input().cinema_id


@pytest.mark.asyncio
async def test_a_failed_save_skips_enrichment(
    command: ImportScreeningsCommand, create_screenings: Mock, enricher: Mock
) -> None:
    """Failures propagate, so nothing runs after the failed step."""
    create_screenings.execute.side_effect = ConnectionError("offline")

    with pytest.raises(ConnectionError):
        await command.execute(_input())

    enricher.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_stored_movies_are_enriched_with_their_identity(
    fetch_screenings: Mock,
    movie_repository: Mock,
    create_screenings: Mock,
    enricher: Mock,
) -> None:
    """Enrichment gets every movie, including the identity matching confirmed."""
    fetch_screenings.execute.return_value = _fetched(
        (FetchedMovie(title="Matched"), FetchedMovie(title="Unmatched")),
        (FetchedScreening("Matched", DAY), FetchedScreening("Unmatched", DAY)),
    )
    command = import_command(
        fetch_screenings,
        movie_repository,
        create_screenings,
        build_matcher(build_match("7")),
        enricher,
    )

    await command.execute(_input())

    movies = enricher.execute.await_args.args[0].movies
    assert sorted(str(movie.tmdb_id) for movie in movies) == ["7", "None"]


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


def test_input_dates_must_be_in_order() -> None:
    """The start date can't come after the end date."""
    with pytest.raises(ValueError):
        ImportScreeningsCommand.InputData("cin-1", date(2026, 11, 2), date(2026, 11, 1))


@pytest.mark.asyncio
async def test_enrichment_outage_propagates_after_screenings_are_saved() -> None:
    """A TMDB outage while enriching fails the import once screenings are saved."""
    fetch = autospec_use_case(FetchScreeningsFromSourceQuery)
    fetch.execute.return_value = FetchScreeningsFromSourceQuery.OutputData(
        "cinema",
        "Cinema",
        "source",
        (FetchScreeningsFromSourceQuery.FetchedMovieData(title="Film"),),
        (FetchScreeningsFromSourceQuery.FetchedScreeningData("Film", DAY),),
    )
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_tmdb_id.return_value = None
    movies.find_by_titles.return_value = []
    movies.create_or_reuse.side_effect = lambda movie: movie
    create_screenings = autospec_use_case(CreateScreeningsCommand)
    create_screenings.execute.return_value = CreateScreeningsCommand.OutputData(
        (), 1, 0, 0, 0
    )
    provider = create_autospec(MetadataRepository, instance=True)
    provider.movie_details.return_value = MetadataBatch(
        (), complete=False, failure=MetadataUnavailableError("provider down")
    )
    metadata_movies = create_autospec(MovieMetadataRepository, instance=True)
    metadata_movies.get.side_effect = lambda movie_id: MovieMetadataSnapshot(
        movie_id, "1", MovieMetadataValues(title="Film"), tmdb_id="1"
    )
    enricher = EnrichMoviesUseCase(
        metadata_movies, provider, lambda: datetime(2026, 10, 31, tzinfo=UTC)
    )
    command = import_command(
        fetch, movies, create_screenings, build_matcher(build_match("1")), enricher
    )
    with pytest.raises(MetadataUnavailableError, match="provider down"):
        await command.execute(
            command.InputData("cinema", date(2026, 10, 31), DAY.date())
        )
    create_screenings.execute.assert_awaited_once()
    metadata_movies.update_metadata.assert_not_awaited()
