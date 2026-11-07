"""Import-time movie identity resolution tests."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions.movie import MovieIdentityConflictError
from marquise.application.metadata import ProviderIdentity
from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from support.movie_import import Outcome, build_match, build_matcher, build_movie_import


@pytest.mark.asyncio
async def test_reuses_movie_by_tmdb_id_without_changing_its_details() -> None:
    """A translated title reuses the existing film, leaving its metadata intact."""
    repo = create_autospec(MovieRepository, instance=True)
    existing = Movie(
        id=MovieId(value="existing"),
        title="Doomsday",
        poster_url="original",
        tmdb_id="123",
    )
    repo.find_by_tmdb_id.return_value = existing
    matcher = build_matcher(build_match("123"))
    command = build_movie_import(repo, matcher)

    result = await command.execute(
        command.InputData(
            movies=(command.build_movie_input(title="Docteur Doom", release_year=2026),)
        )
    )

    assert result.movies == (command.MovieData(title="Docteur Doom", id="existing"),)
    request = matcher.execute.await_args.args[0].movies[0]
    assert (request.title, request.release_year) == ("Docteur Doom", 2026)
    repo.find_by_tmdb_id.assert_awaited_once_with("123")
    repo.create_or_reuse.assert_not_awaited()


@pytest.mark.asyncio
async def test_saves_tmdb_id_for_new_movie() -> None:
    """A single TMDB hit with no saved movie gives the new movie an id."""
    repo = create_autospec(MovieRepository, instance=True)
    matcher = build_matcher(build_match("44"))
    repo.find_by_tmdb_id.return_value = None
    repo.find_by_titles.return_value = []
    repo.create_or_reuse.side_effect = lambda movie: movie
    command = build_movie_import(repo, matcher)

    result = await command.execute(
        command.InputData(
            movies=(command.build_movie_input(title="New Movie", release_year=2026),)
        )
    )

    assert result.movies[0].title == "New Movie"
    assert repo.create_or_reuse.call_args.args[0].tmdb_id == "44"


@pytest.mark.asyncio
async def test_same_tmdb_film_twice_in_one_import_creates_one_movie() -> None:
    """Two localized titles in a batch share the newly saved movie."""
    repo = create_autospec(MovieRepository, instance=True)
    matcher = build_matcher(build_match("44"), build_match("44"))
    repo.find_by_tmdb_id.return_value = None
    repo.find_by_titles.return_value = []
    repo.create_or_reuse.side_effect = lambda movie: movie
    command = build_movie_import(repo, matcher)

    output = await command.execute(
        command.InputData(
            movies=(
                command.build_movie_input(title="Doomsday", release_year=2026),
                command.build_movie_input(title="Docteur Doom", release_year=2026),
            )
        )
    )

    assert {movie.title for movie in output.movies} == {"Doomsday", "Docteur Doom"}
    assert len({movie.id for movie in output.movies}) == 1
    repo.create_or_reuse.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["unmatched", "incomplete"])
async def test_unclear_tmdb_result_keeps_title_fallback(status: str) -> None:
    """No match or an incomplete search cannot authorize a movie merge."""
    repo = create_autospec(MovieRepository, instance=True)
    matcher = build_matcher(Outcome(status))
    repo.find_by_titles.return_value = []
    repo.create_or_reuse.side_effect = lambda movie: movie
    command = build_movie_import(repo, matcher)

    await command.execute(
        command.InputData(movies=(command.build_movie_input(title="It"),))
    )

    assert repo.create_or_reuse.call_args.args[0].tmdb_id is None
    repo.find_by_tmdb_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_conflicting_tmdb_id_never_reuses_a_same_title_movie() -> None:
    """A same-title movie with another known identity must not own the screening."""
    repo = create_autospec(MovieRepository, instance=True)
    repo.find_by_tmdb_id.return_value = None
    repo.find_by_titles.return_value = [
        Movie(id=MovieId("old"), title="Same Title", tmdb_id="111")
    ]
    matcher = build_matcher(build_match("222"))
    command = build_movie_import(repo, matcher)

    with pytest.raises(MovieIdentityConflictError):
        await command.execute(
            command.InputData(movies=(command.build_movie_input(title="Same Title"),))
        )

    repo.create_or_reuse.assert_not_awaited()


@pytest.mark.asyncio
async def test_other_provider_id_cannot_be_used_as_a_tmdb_id() -> None:
    """A future service's ids do not claim TMDB movie identities."""
    repo = create_autospec(MovieRepository, instance=True)
    matcher = build_matcher(Outcome("matched", ProviderIdentity("other", "44")))
    repo.find_by_titles.return_value = []
    repo.create_or_reuse.side_effect = lambda movie: movie
    command = build_movie_import(repo, matcher)

    await command.execute(
        command.InputData(movies=(command.build_movie_input(title="New Movie"),))
    )

    repo.find_by_tmdb_id.assert_not_awaited()
    assert repo.create_or_reuse.call_args.args[0].tmdb_id is None


@pytest.mark.asyncio
async def test_distinct_tmdb_ids_survive_colliding_title_keys() -> None:
    """Different films keep separate rows even when their title keys collide."""
    repo = create_autospec(MovieRepository, instance=True)
    matcher = build_matcher(build_match("1"), build_match("2"))
    repo.find_by_tmdb_id.return_value = None
    repo.find_by_titles.return_value = []
    repo.create_or_reuse.side_effect = lambda movie: movie
    command = build_movie_import(repo, matcher)

    output = await command.execute(
        command.InputData(
            movies=(
                command.build_movie_input(title="The Thing", release_year=1982),
                command.build_movie_input(title="Thing", release_year=2026),
            )
        )
    )

    assert {movie.title for movie in output.movies} == {"The Thing", "Thing"}
    assert len({movie.id for movie in output.movies}) == 2
    assert {call.args[0].tmdb_id for call in repo.create_or_reuse.await_args_list} == {
        "1",
        "2",
    }


@pytest.mark.asyncio
async def test_distinct_identity_ignores_a_different_canonical_title_match() -> None:
    """A known different identity cannot block a distinct exact title."""
    repo = create_autospec(MovieRepository, instance=True)
    matcher = build_matcher(build_match("2"))
    repo.find_by_tmdb_id.return_value = None
    repo.find_by_titles.return_value = [
        Movie(id=MovieId("old"), title="The Thing", tmdb_id="1")
    ]
    repo.create_or_reuse.side_effect = lambda movie: movie
    command = build_movie_import(repo, matcher)

    output = await command.execute(
        command.InputData(movies=(command.build_movie_input(title="Thing"),))
    )

    assert output.movies[0].id != "old"
    assert repo.create_or_reuse.call_args.args[0].tmdb_id == "2"
