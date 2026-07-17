"""Tests for GetMoviesByIdsUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import TooManyMovieIdsError
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.get_movies_by_ids import GetMoviesByIdsUseCase
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


@pytest.mark.asyncio
async def test_get_movies_by_ids_returns_matching_movies() -> None:
    """The use case maps found movies to their output data."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_by_ids.return_value = [
        Movie(id=MovieId(value="mov-1"), title="The Odyssey", release_year=2026),
        Movie(id=MovieId(value="mov-2"), title="Sunrise", release_year=2025),
    ]

    use_case = GetMoviesByIdsUseCase(movie_repository=mock_repo)
    result = await use_case.execute(
        GetMoviesByIdsUseCase.InputData(movie_ids=("mov-1", "mov-2"))
    )

    assert [m.id for m in result.movies] == ["mov-1", "mov-2"]
    assert [m.title for m in result.movies] == ["The Odyssey", "Sunrise"]
    mock_repo.find_by_ids.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_movies_by_ids_omits_missing_ids() -> None:
    """IDs with no matching movie are silently omitted, not an error."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_by_ids.return_value = [
        Movie(id=MovieId(value="mov-1"), title="The Odyssey"),
    ]

    use_case = GetMoviesByIdsUseCase(movie_repository=mock_repo)
    result = await use_case.execute(
        GetMoviesByIdsUseCase.InputData(movie_ids=("mov-1", "missing"))
    )

    assert [m.id for m in result.movies] == ["mov-1"]


def test_get_movies_by_ids_input_rejects_empty_list() -> None:
    """An empty movie_ids tuple is rejected at input validation."""
    with pytest.raises(ValueError, match="movie_ids must not be empty"):
        GetMoviesByIdsUseCase.InputData(movie_ids=())


def test_get_movies_by_ids_input_rejects_too_many_ids() -> None:
    """More than MAX_MOVIE_IDS ids is rejected at input validation."""
    too_many = tuple(f"mov-{i}" for i in range(101))
    with pytest.raises(TooManyMovieIdsError):
        GetMoviesByIdsUseCase.InputData(movie_ids=too_many)
