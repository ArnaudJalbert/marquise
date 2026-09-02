"""Tests for DeleteScreeningUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import MovieRepository, ScreeningRepository
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime


@pytest.fixture
def screening() -> Screening:
    """Provide screening linked to movie eligible for orphan cleanup."""
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=Movie(id=MovieId(value="mov-1"), title="Movie One"),
        cinema=Cinema(id=CinemaId(value="cin-1"), name="Cinema One"),
        showtime=Showtime(value=datetime(2026, 6, 27, 19, 30, tzinfo=UTC)),
    )


@pytest.fixture
def screening_repository(screening: Screening) -> ScreeningRepository:
    """Provide autospecced screening repository."""
    repository = create_autospec(ScreeningRepository, instance=True)
    repository.find_by_id.return_value = screening
    return repository


@pytest.fixture
def movie_repository() -> MovieRepository:
    """Provide autospecced movie repository."""
    return create_autospec(MovieRepository, instance=True)


@pytest.fixture
def use_case(
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
) -> DeleteScreeningUseCase:
    """Provide configured delete-screening use case."""
    return DeleteScreeningUseCase(
        screening_repository=screening_repository,
        movie_repository=movie_repository,
    )


@pytest.mark.asyncio
async def test_deletes_screening_and_cleans_orphan_movie(
    use_case: DeleteScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
) -> None:
    """Successful delete requests atomic orphan cleanup for linked movie."""
    result = await use_case.execute(
        DeleteScreeningUseCase.InputData(screening_id="scr-1")
    )

    assert result.screening_id == "scr-1"
    screening_repository.find_by_id.assert_awaited_once_with(ScreeningId(value="scr-1"))
    screening_repository.delete.assert_awaited_once_with(
        screening_id=ScreeningId(value="scr-1")
    )
    movie_repository.delete_if_orphan.assert_awaited_once_with(MovieId(value="mov-1"))


@pytest.mark.asyncio
async def test_missing_screening_stops_before_delete(
    use_case: DeleteScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
) -> None:
    """Missing screening error prevents delete and orphan cleanup calls."""
    screening_repository.find_by_id.side_effect = ScreeningNotFoundError(
        "A screening with ID 'scr-missing' was not found"
    )

    with pytest.raises(ScreeningNotFoundError, match="scr-missing"):
        await use_case.execute(
            DeleteScreeningUseCase.InputData(screening_id="scr-missing")
        )

    screening_repository.delete.assert_not_awaited()
    movie_repository.delete_if_orphan.assert_not_awaited()


def test_input_rejects_empty_screening_id() -> None:
    """Empty screening_id is rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        DeleteScreeningUseCase.InputData(screening_id="  ")
