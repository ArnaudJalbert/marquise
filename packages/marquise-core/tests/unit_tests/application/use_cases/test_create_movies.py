"""Creating one movie per film and tying every source movie to it."""

from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_movies import CreateMoviesCommand

MovieInput = CreateMoviesCommand.MovieInput


def _movies() -> Mock:
    movies = create_autospec(MovieRepository, instance=True)
    movies.create_or_reuse.side_effect = lambda movie: movie
    return movies


@pytest.mark.asyncio
async def test_creates_a_movie_with_every_detail() -> None:
    """The saved movie uses the saved title and the source details."""
    movies = _movies()
    command = CreateMoviesCommand(movies)

    output = await command.execute(
        command.InputData(
            (
                MovieInput(
                    "Dune",
                    "Dune (2021)",
                    "tmdb:7",
                    tmdb_id="7",
                    release_year=2021,
                    description="Sand",
                ),
            )
        )
    )

    saved_movie = movies.create_or_reuse.await_args.args[0]
    assert saved_movie.title == "Dune (2021)"
    assert saved_movie.tmdb_id == "7"
    assert saved_movie.release_year == 2021
    assert saved_movie.description == "Sand"
    assert output.movies == (
        command.CreatedMovie("Dune", None, saved_movie.id.value, "7"),
    )


@pytest.mark.asyncio
async def test_sources_sharing_a_key_share_one_movie() -> None:
    """Two source movies of one film create it once."""
    movies = _movies()
    command = CreateMoviesCommand(movies)

    output = await command.execute(
        command.InputData(
            (
                MovieInput("Doomsday", "Doomsday", "tmdb:7", tmdb_id="7"),
                MovieInput("Docteur Doom", "Docteur Doom", "tmdb:7", tmdb_id="7"),
            )
        )
    )

    movies.create_or_reuse.assert_awaited_once()
    assert len({movie.movie_id for movie in output.movies}) == 1
    assert {movie.title for movie in output.movies} == {"Doomsday", "Docteur Doom"}


@pytest.mark.asyncio
@pytest.mark.parametrize("matched_first", [True, False])
async def test_the_movie_with_an_identity_wins_its_key(matched_first: bool) -> None:
    """Whatever the order, the created movie carries the TMDB identity."""
    movies = _movies()
    command = CreateMoviesCommand(movies)
    matched = MovieInput("Fjord", "Fjord", "tmdb:7", tmdb_id="7")
    unmatched = MovieInput("Fjord (VOSTA)", "Fjord (VOSTA)", "tmdb:7")
    pair = (matched, unmatched) if matched_first else (unmatched, matched)

    await command.execute(command.InputData(pair))

    assert movies.create_or_reuse.await_args.args[0].tmdb_id == "7"


@pytest.mark.asyncio
async def test_first_unmatched_movie_wins_its_key() -> None:
    """Among movies without an identity, the first one is created."""
    movies = _movies()
    command = CreateMoviesCommand(movies)

    await command.execute(
        command.InputData(
            (
                MovieInput("First", "First", "title:same"),
                MovieInput("Second", "Second", "title:same"),
            )
        )
    )

    assert movies.create_or_reuse.await_args.args[0].title == "First"


@pytest.mark.parametrize(
    "fields",
    [
        {"title": 1, "saved_title": "Film", "key": "title:film"},
        {"title": "Film", "saved_title": 1, "key": "title:film"},
        {"title": "Film", "saved_title": "Film", "key": "k", "directors": ["One"]},
        {"title": "Film", "saved_title": "Film", "key": "k", "release_year": "2026"},
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
        CreateMoviesCommand.InputData(movies=movies)
