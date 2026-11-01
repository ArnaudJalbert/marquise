"""Tests for GetMovieUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


@pytest.mark.asyncio
async def test_get_movie_returns_movie() -> None:
    """The use case maps a found movie to its output data."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_by_id.return_value = Movie(
        id=MovieId(value="mov-1"),
        title="The Odyssey",
        release_year=2026,
        directors=("Jane Director",),
        tmdb_rating=8.1,
        tmdb_vote_count=1234,
    )

    use_case = GetMovieUseCase(movie_repository=mock_repo)
    result = await use_case.execute(GetMovieUseCase.InputData(movie_id="mov-1"))

    assert result.id == "mov-1"
    assert result.title == "The Odyssey"
    assert result.directors == ("Jane Director",)
    assert result.tmdb_rating == 8.1 and result.tmdb_vote_count == 1234
    mock_repo.find_by_id.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_movie_raises_when_missing() -> None:
    """The use case raises MovieNotFoundError when the repo returns None."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_by_id.return_value = None

    use_case = GetMovieUseCase(movie_repository=mock_repo)
    with pytest.raises(MovieNotFoundError):
        await use_case.execute(GetMovieUseCase.InputData(movie_id="missing"))


def test_get_movie_input_rejects_empty_id() -> None:
    """Empty movie_id is rejected at input validation."""
    with pytest.raises(ValueError, match="movie_id must not be empty"):
        GetMovieUseCase.InputData(movie_id="  ")
