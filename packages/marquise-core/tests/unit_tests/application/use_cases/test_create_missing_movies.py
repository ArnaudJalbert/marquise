"""Tests for CreateMissingMoviesCommand."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


def _make_movie_input(
    title: str = "Test Movie",
    description: str | None = None,
    directors: tuple[str, ...] | None = None,
    cast: tuple[str, ...] | None = None,
    duration_minutes: int | None = None,
    release_year: int | None = None,
) -> CreateMissingMoviesCommand.MovieInput:
    return CreateMissingMoviesCommand.MovieInput(
        title=title,
        description=description,
        directors=directors,
        cast=cast,
        duration_minutes=duration_minutes,
        release_year=release_year,
    )


def _make_command(
    movie_repo: MovieRepository,
) -> CreateMissingMoviesCommand:
    return CreateMissingMoviesCommand(movie_repository=movie_repo)


async def _run(
    command: CreateMissingMoviesCommand,
    movies: tuple[CreateMissingMoviesCommand.MovieInput, ...],
) -> dict[str, str]:
    result = await command.execute(CreateMissingMoviesCommand.InputData(movies=movies))
    return {m.title: m.id for m in result.movies}


@pytest.mark.asyncio
async def test_creates_missing_movies_with_all_metadata() -> None:
    """Test that a missing movie is created with all provided metadata."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_titles.return_value = []
    saved_movie = Movie(
        id=MovieId(value="mov-new"),
        title="New Movie",
        description="A great movie",
        directors=("Director A",),
        duration_minutes=120,
        release_year=2026,
    )
    mock_movie_repo.save.return_value = saved_movie

    lookup = await _run(
        _make_command(mock_movie_repo),
        (
            _make_movie_input(
                "New Movie",
                description="A great movie",
                directors=("Director A",),
                duration_minutes=120,
                release_year=2026,
            ),
        ),
    )

    assert lookup["New Movie"] == "mov-new"
    mock_movie_repo.save.assert_awaited_once()
    saved = mock_movie_repo.save.call_args[0][0]
    assert saved.description == "A great movie"
    assert saved.directors == ("Director A",)
    assert saved.duration_minutes == 120
    assert saved.release_year == 2026


@pytest.mark.asyncio
async def test_creates_bare_movie_when_no_metadata() -> None:
    """Test that a missing movie is created with just a title."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_titles.return_value = []
    saved_movie = Movie(id=MovieId(value="mov-bare"), title="Bare Movie")
    mock_movie_repo.save.return_value = saved_movie

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("Bare Movie"),),
    )

    assert lookup["Bare Movie"] == "mov-bare"
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_skips_existing_movies() -> None:
    """Test that existing movies are not created again."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    existing_movie = Movie(id=MovieId(value="mov-existing"), title="Existing Movie")
    mock_movie_repo.find_by_titles.return_value = [existing_movie]

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("Existing Movie"),),
    )

    assert lookup["Existing Movie"] == "mov-existing"
    mock_movie_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_returns_lookup_for_all_inputs() -> None:
    """Test that both existing and new movies appear in the lookup."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    existing_movie = Movie(id=MovieId(value="mov-existing"), title="Existing Movie")
    mock_movie_repo.find_by_titles.return_value = [existing_movie]
    saved_movie = Movie(id=MovieId(value="mov-new"), title="New Movie")
    mock_movie_repo.save.return_value = saved_movie

    lookup = await _run(
        _make_command(mock_movie_repo),
        (
            _make_movie_input("Existing Movie"),
            _make_movie_input("New Movie"),
        ),
    )

    assert lookup["Existing Movie"] == "mov-existing"
    assert lookup["New Movie"] == "mov-new"
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_dedupes_titles_differing_by_whitespace() -> None:
    """Test that titles differing only by whitespace are treated as the same."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_titles.return_value = []
    saved_movie = Movie(id=MovieId(value="mov-a"), title="Beau Is Afraid")
    mock_movie_repo.save.return_value = saved_movie

    lookup = await _run(
        _make_command(mock_movie_repo),
        (
            _make_movie_input("Beau Is Afraid"),
            _make_movie_input("  Beau  Is  Afraid "),
        ),
    )

    mock_movie_repo.save.assert_awaited_once()
    assert lookup["Beau Is Afraid"] == "mov-a"


@pytest.mark.asyncio
async def test_reuses_movie_found_with_different_case() -> None:
    """Test that a case-insensitive match still returns the correct lookup."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    existing_movie = Movie(id=MovieId(value="mov-batman"), title="the batman")
    mock_movie_repo.find_by_titles.return_value = [existing_movie]

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("The Batman"),),
    )

    assert lookup["The Batman"] == "mov-batman"
    mock_movie_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_reuses_movie_when_source_omits_leading_article() -> None:
    """Test that Odyssey matches an existing movie titled The Odyssey."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    existing_movie = Movie(id=MovieId(value="mov-odyssey"), title="The Odyssey")
    mock_movie_repo.find_by_titles.return_value = [existing_movie]

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("ODYSSEY"),),
    )

    assert lookup["ODYSSEY"] == "mov-odyssey"
    mock_movie_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_reuses_movie_when_colon_differs() -> None:
    """Test that punctuation such as a colon does not split one movie."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    existing_movie = Movie(
        id=MovieId(value="mov-odyssey"), title="The Odyssey: Part One"
    )
    mock_movie_repo.find_by_titles.return_value = [existing_movie]

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("The Odyssey Part One"),),
    )

    assert lookup["The Odyssey Part One"] == "mov-odyssey"
    mock_movie_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_creates_movie_when_title_candidate_has_different_key() -> None:
    """Test that a contained title candidate does not become a movie match."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_titles.return_value = [
        Movie(id=MovieId(value="mov-it-two"), title="It: Chapter Two")
    ]
    mock_movie_repo.save.return_value = Movie(id=MovieId(value="mov-it"), title="It")

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("It"),),
    )

    assert lookup["It"] == "mov-it"
    mock_movie_repo.find_by_titles.assert_awaited_once_with(["it"])
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_creates_movie_when_existing_match_has_conflicting_release_year() -> None:
    """Test that a canonical title with another release year is not reused."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_titles.return_value = [
        Movie(id=MovieId(value="mov-2026"), title="The Odyssey", release_year=2026)
    ]
    mock_movie_repo.save.return_value = Movie(
        id=MovieId(value="mov-1997"), title="ODYSSEY", release_year=1997
    )

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("ODYSSEY", release_year=1997),),
    )

    assert lookup["ODYSSEY"] == "mov-1997"
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_creates_movie_when_canonical_match_is_ambiguous() -> None:
    """Test that multiple canonical candidates are not chosen arbitrarily."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_titles.return_value = [
        Movie(id=MovieId(value="mov-a"), title="The Odyssey"),
        Movie(id=MovieId(value="mov-b"), title="Odyssey!"),
    ]
    mock_movie_repo.save.return_value = Movie(
        id=MovieId(value="mov-new"), title="ODYSSEY"
    )

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("ODYSSEY"),),
    )

    assert lookup["ODYSSEY"] == "mov-new"
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_dedupes_titles_after_ignoring_articles_and_punctuation() -> None:
    """Test that equivalent source titles create one movie."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_titles.return_value = []
    mock_movie_repo.save.side_effect = [
        Movie(id=MovieId(value="mov-odyssey"), title="ODYSSEY")
    ]

    lookup = await _run(
        _make_command(mock_movie_repo),
        (_make_movie_input("The Odyssey"), _make_movie_input("ODYSSEY!")),
    )

    mock_movie_repo.save.assert_awaited_once()
    assert lookup["ODYSSEY!"] == "mov-odyssey"
