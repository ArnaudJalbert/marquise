"""Creating one movie per film."""

from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_movies import CreateMoviesCommand

MovieInput = CreateMoviesCommand.MovieInput


@pytest.fixture
def movie_repository() -> Mock:
    """A repository that saves whatever it is given."""
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.create_or_reuse.side_effect = lambda movie: movie
    return movie_repository


@pytest.fixture
def command(movie_repository: Mock) -> CreateMoviesCommand:
    """The command under test."""
    return CreateMoviesCommand(movie_repository)


@pytest.mark.asyncio
async def test_creates_a_movie_with_every_detail(
    command: CreateMoviesCommand, movie_repository: Mock
) -> None:
    """The saved movie uses the saved title and the source details."""
    output = await command.execute(
        command.InputData(
            (
                MovieInput(
                    "Dune (2021)",
                    "tmdb:7",
                    tmdb_id="7",
                    release_year=2021,
                    description="Sand",
                ),
            )
        )
    )

    saved_movie = movie_repository.create_or_reuse.await_args.args[0]
    assert saved_movie.title == "Dune (2021)"
    assert saved_movie.tmdb_id == "7"
    assert saved_movie.release_year == 2021
    assert saved_movie.description == "Sand"
    assert output.movie_ids == (saved_movie.id.value,)


@pytest.mark.asyncio
async def test_sources_sharing_a_key_create_one_movie(
    command: CreateMoviesCommand, movie_repository: Mock
) -> None:
    """Two source movies of one film create it once, and return one ID."""
    output = await command.execute(
        command.InputData(
            (
                MovieInput("Doomsday", "tmdb:7", tmdb_id="7"),
                MovieInput("Docteur Doom", "tmdb:7", tmdb_id="7"),
            )
        )
    )

    movie_repository.create_or_reuse.assert_awaited_once()
    assert len(output.movie_ids) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("matched_first", [True, False])
async def test_the_movie_with_an_identity_wins_its_key(
    command: CreateMoviesCommand, movie_repository: Mock, matched_first: bool
) -> None:
    """Whatever the order, the created movie carries the TMDB identity."""
    matched = MovieInput("Fjord", "tmdb:7", tmdb_id="7")
    unmatched = MovieInput("Fjord (VOSTA)", "tmdb:7")
    pair = (matched, unmatched) if matched_first else (unmatched, matched)

    await command.execute(command.InputData(pair))

    assert movie_repository.create_or_reuse.await_args.args[0].tmdb_id == "7"


@pytest.mark.asyncio
async def test_first_unmatched_movie_wins_its_key(
    command: CreateMoviesCommand, movie_repository: Mock
) -> None:
    """Among movies without an identity, the first one is created."""
    await command.execute(
        command.InputData(
            (
                MovieInput("First", "title:same"),
                MovieInput("Second", "title:same"),
            )
        )
    )

    assert movie_repository.create_or_reuse.await_args.args[0].title == "First"


@pytest.mark.parametrize(
    "fields",
    [
        {"saved_title": 1, "key": "title:film"},
        {"saved_title": "Film", "key": 1},
        {"saved_title": "Film", "key": "k", "directors": ["One"]},
        {"saved_title": "Film", "key": "k", "release_year": "2026"},
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
