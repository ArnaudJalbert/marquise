"""Sorting source movies into stored and missing, without writing anything."""

from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions.movie import MovieIdentityConflictError
from marquise.application.metadata import ProviderIdentity
from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId

MovieInput = FindStoredMoviesQuery.MovieInput
TMDB_7 = ProviderIdentity("tmdb", "7")


def _movies(*found: Movie) -> Mock:
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_tmdb_id.return_value = None
    movies.find_by_titles.return_value = list(found)
    return movies


@pytest.mark.asyncio
async def test_stored_identity_links_without_a_title_search_term() -> None:
    """A known TMDB identity wins, and the source title is kept."""
    movies = _movies()
    movies.find_by_tmdb_id.return_value = Movie(
        id=MovieId(value="stored"), title="Doomsday", tmdb_id="7"
    )
    query = FindStoredMoviesQuery(movies)

    output = await query.execute(
        query.InputData((MovieInput("Docteur Doom", identity=TMDB_7),))
    )

    assert output.stored == (query.StoredMovie("Docteur Doom", None, "stored", "7"),)
    assert output.missing == ()
    movies.find_by_titles.assert_awaited_once_with([])


@pytest.mark.asyncio
async def test_missing_matched_movie_is_keyed_by_identity() -> None:
    """A new identity is missing, with the year TMDB supplied."""
    query = FindStoredMoviesQuery(_movies())

    output = await query.execute(
        query.InputData(
            (MovieInput("Film", identity=TMDB_7, matched_release_year=2026),)
        )
    )

    assert output.missing == (
        query.MissingMovie("Film", None, "Film", 2026, "7", "tmdb:7"),
    )


@pytest.mark.asyncio
async def test_source_year_beats_the_matched_year() -> None:
    """The source's own year is only filled in when it has none."""
    query = FindStoredMoviesQuery(_movies())

    output = await query.execute(
        query.InputData(
            (
                MovieInput(
                    "Film",
                    release_year=2025,
                    matched_release_year=2026,
                    identity=TMDB_7,
                ),
            )
        )
    )

    assert output.missing[0].release_year == 2025


@pytest.mark.asyncio
async def test_unmatched_movie_finds_a_stored_title() -> None:
    """With no identity, a stored title is enough."""
    query = FindStoredMoviesQuery(
        _movies(Movie(id=MovieId(value="stored"), title="Gentle Monster"))
    )

    output = await query.execute(
        query.InputData((MovieInput("Gentle Monster (VOSTA)", "source-1"),))
    )

    assert output.stored == (
        query.StoredMovie("Gentle Monster (VOSTA)", "source-1", "stored", None),
    )


@pytest.mark.asyncio
async def test_label_variant_shares_the_matched_key() -> None:
    """An unmatched variant of a matched title belongs to the same film."""
    query = FindStoredMoviesQuery(_movies())

    output = await query.execute(
        query.InputData(
            (MovieInput("Fjord", identity=TMDB_7), MovieInput("Fjord (VOSTA)"))
        )
    )

    assert {movie.key for movie in output.missing} == {"tmdb:7"}


@pytest.mark.asyncio
async def test_remake_takes_its_year_in_the_saved_title_only() -> None:
    """Another film owns the title, so the remake is saved with its year."""
    query = FindStoredMoviesQuery(
        _movies(Movie(id=MovieId(value="old"), title="Odyssey", tmdb_id="1"))
    )

    output = await query.execute(
        query.InputData((MovieInput("Odyssey", release_year=2021, identity=TMDB_7),))
    )

    assert output.missing[0].title == "Odyssey"
    assert output.missing[0].saved_title == "Odyssey (2021)"


@pytest.mark.asyncio
async def test_remake_without_a_year_raises() -> None:
    """Without a year, the two films can't be told apart."""
    query = FindStoredMoviesQuery(
        _movies(Movie(id=MovieId(value="old"), title="Odyssey", tmdb_id="1"))
    )

    with pytest.raises(MovieIdentityConflictError):
        await query.execute(query.InputData((MovieInput("Odyssey", identity=TMDB_7),)))


@pytest.mark.parametrize(
    "fields",
    [
        {"title": 1},
        {"title": "Film", "release_year": "2026"},
        {"title": "Film", "identity": "7"},
        {"title": "Film", "matched_titles": ["Film"]},
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
        FindStoredMoviesQuery.InputData(movies=movies)
