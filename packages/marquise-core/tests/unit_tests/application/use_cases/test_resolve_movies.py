"""Tests for ResolveMoviesCommand, the movie resolution coordinator."""

from unittest.mock import Mock

import pytest

from marquise.application.exceptions.movie import MovieMetadataUnavailableError
from marquise.application.metadata import ProviderIdentity
from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
from marquise.application.use_cases.create_movies import CreateMoviesCommand
from marquise.application.use_cases.match_movies import MatchMoviesUseCase
from marquise.application.use_cases.resolve_movies import ResolveMoviesCommand
from support.movie_import import autospec_use_case

MovieInput = ResolveMoviesCommand.MovieInput
IDENTITY = ProviderIdentity("tmdb", "7")


def _matcher(status: str = "unmatched") -> Mock:
    matcher = autospec_use_case(MatchMoviesUseCase)
    matcher.execute.side_effect = lambda request: MatchMoviesUseCase.OutputData(
        tuple(
            MatchMoviesUseCase.MovieMatch(
                movie, status, IDENTITY, ("Other Title",), 2026
            )
            for movie in request.movies
        )
    )
    return matcher


def _finder(
    stored: tuple = (),
    missing: tuple = (),
) -> Mock:
    finder = autospec_use_case(FindStoredMoviesQuery)
    finder.execute.return_value = FindStoredMoviesQuery.OutputData(stored, missing)
    return finder


def _creator() -> Mock:
    creator = autospec_use_case(CreateMoviesCommand)
    creator.execute.side_effect = lambda request: CreateMoviesCommand.OutputData(
        tuple(
            CreateMoviesCommand.CreatedMovie(
                movie.title, movie.source_identifier, "created", movie.tmdb_id
            )
            for movie in request.movies
        )
    )
    return creator


@pytest.mark.asyncio
async def test_passes_match_results_to_the_stored_movie_lookup() -> None:
    """The lookup sees the source movie and what matching found for it."""
    finder = _finder()
    command = ResolveMoviesCommand(_matcher("matched"), finder, _creator())

    await command.execute(
        command.InputData((MovieInput("Film", "one", release_year=2025),))
    )

    assert finder.execute.await_args.args[0].movies == (
        FindStoredMoviesQuery.MovieInput(
            "Film", "one", 2025, 2026, IDENTITY, ("Other Title",)
        ),
    )


@pytest.mark.asyncio
async def test_missing_movies_are_created_with_their_source_details() -> None:
    """Creation gets the lookup's decisions and the source's details."""
    missing = FindStoredMoviesQuery.MissingMovie(
        "Film", "one", "Film (2026)", 2026, "7", "tmdb:7"
    )
    creator = _creator()
    command = ResolveMoviesCommand(_matcher(), _finder(missing=(missing,)), creator)

    await command.execute(
        command.InputData((MovieInput("Film", "one", description="Sand"),))
    )

    created = creator.execute.await_args.args[0].movies[0]
    assert (created.saved_title, created.key, created.description) == (
        "Film (2026)",
        "tmdb:7",
        "Sand",
    )


@pytest.mark.asyncio
async def test_returns_stored_and_created_movies() -> None:
    """Every source movie comes back with its movie ID."""
    stored = FindStoredMoviesQuery.StoredMovie("Old", "one", "stored", "1")
    missing = FindStoredMoviesQuery.MissingMovie(
        "New", "two", "New", None, None, "title:new"
    )
    command = ResolveMoviesCommand(
        _matcher(), _finder((stored,), (missing,)), _creator()
    )

    output = await command.execute(
        command.InputData((MovieInput("Old", "one"), MovieInput("New", "two")))
    )

    assert output.movies == (
        command.ResolvedMovie("Old", "one", "stored", "1"),
        command.ResolvedMovie("New", "two", "created", None),
    )


@pytest.mark.asyncio
async def test_a_matching_outage_stops_before_any_lookup_or_creation() -> None:
    """Failures propagate, so nothing runs after the failed step."""
    matcher = _matcher()
    matcher.execute.side_effect = MovieMetadataUnavailableError("offline")
    finder = _finder()
    creator = _creator()
    command = ResolveMoviesCommand(matcher, finder, creator)

    with pytest.raises(MovieMetadataUnavailableError):
        await command.execute(command.InputData((MovieInput("Film"),)))

    finder.execute.assert_not_awaited()
    creator.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "fields",
    [
        {"title": 1},
        {"title": "Film", "release_year": "2026"},
        {"title": "Film", "directors": ["One"]},
        {"title": "Film", "description": 1},
    ],
)
def test_movie_input_rejects_wrong_types(fields: dict) -> None:
    """Input is the one place types are checked."""
    with pytest.raises(TypeError):
        MovieInput(**fields)


@pytest.mark.parametrize("movies", [["Film"], ("Film",)])
def test_input_rejects_wrong_types(movies: object) -> None:
    """The batch must be a tuple of movie inputs."""
    with pytest.raises(TypeError):
        ResolveMoviesCommand.InputData(movies=movies)
