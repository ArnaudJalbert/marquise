"""Tests for GetScreeningUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases.get_screening import GetScreeningUseCase
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime


@pytest.mark.asyncio
async def test_returns_screening_when_found() -> None:
    """The use case returns the screening mapped to output data."""
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    movie = Movie(id=MovieId(value="mov-1"), title="The Odyssey")
    screening = Screening(
        id=ScreeningId(value="scr-1"),
        movie=movie,
        cinema=cinema,
        showtime=Showtime(value=datetime(2026, 6, 27, 19, 30, tzinfo=UTC)),
    )
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_by_id.return_value = screening

    use_case = GetScreeningUseCase(screening_repository=screening_repo)
    result = await use_case.execute(GetScreeningUseCase.InputData(screening_id="scr-1"))

    assert result.id == "scr-1"
    assert result.movie_id == "mov-1"
    assert result.movie_title == "The Odyssey"
    assert result.cinema_id == "cin-1"
    assert result.cinema_name == "Cinema One"
    assert result.showtime.startswith("2026-06-27T19:30")
    screening_repo.find_by_id.assert_awaited_once_with(ScreeningId(value="scr-1"))


@pytest.mark.asyncio
async def test_raises_when_screening_missing() -> None:
    """A missing screening raises ScreeningNotFoundError."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_by_id.return_value = None

    use_case = GetScreeningUseCase(screening_repository=screening_repo)
    with pytest.raises(ScreeningNotFoundError):
        await use_case.execute(GetScreeningUseCase.InputData(screening_id="missing"))


def test_input_rejects_empty_screening_id() -> None:
    """An empty screening_id is rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        GetScreeningUseCase.InputData(screening_id="  ")
