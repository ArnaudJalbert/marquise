"""Tests for GetCinemaShowtimesUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository, ScreeningRepository
from marquise.application.use_cases.get_cinema_showtimes import (
    GetCinemaShowtimesUseCase,
)
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)


def _input() -> GetCinemaShowtimesUseCase.InputData:
    return GetCinemaShowtimesUseCase.InputData(
        cinema_id="cin-1",
        start_date=datetime(2026, 6, 27, tzinfo=UTC),
        end_date=datetime(2026, 6, 28, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_returns_cinema_and_screenings() -> None:
    """The use case returns the cinema with its screenings."""
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    movie = Movie(id=MovieId(value="mov-1"), title="The Odyssey")
    screening = Screening(
        id=ScreeningId(value="scr-1"),
        movie=movie,
        cinema=cinema,
        showtime=Showtime(value=datetime(2026, 6, 27, 19, 30, tzinfo=UTC)),
    )
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = cinema
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_by_cinema_and_date_range.return_value = [screening]

    use_case = GetCinemaShowtimesUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    result = await use_case.execute(_input())

    assert result.cinema_name == "Cinema One"
    assert len(result.screenings) == 1
    assert result.screenings[0].movie_title == "The Odyssey"
    assert result.screenings[0].showtime.startswith("2026-06-27T19:30")


@pytest.mark.asyncio
async def test_raises_when_cinema_missing() -> None:
    """A missing cinema raises CinemaNotFoundError before querying screenings."""
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = None
    screening_repo = create_autospec(ScreeningRepository, instance=True)

    use_case = GetCinemaShowtimesUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    with pytest.raises(CinemaNotFoundError):
        await use_case.execute(_input())
    screening_repo.find_by_cinema_and_date_range.assert_not_awaited()


def test_input_rejects_inverted_range() -> None:
    """start_date after end_date is rejected."""
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        GetCinemaShowtimesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 6, 28, tzinfo=UTC),
            end_date=datetime(2026, 6, 27, tzinfo=UTC),
        )


def test_input_rejects_inverted_range_with_mixed_tz_awareness() -> None:
    """An inverted range raises ValueError even when only one side is tz-aware.

    Comparing an aware and a naive datetime directly raises TypeError, not
    ValueError, which the API layer doesn't catch, turning what should be a
    422 into an unhandled 500.
    """
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        GetCinemaShowtimesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 7, 1, tzinfo=UTC),
            end_date=datetime(2026, 6, 30),
        )


def test_input_accepts_valid_range_with_mixed_tz_awareness() -> None:
    """A valid (non-inverted) range does not raise when tz-awareness is mixed."""
    GetCinemaShowtimesUseCase.InputData(
        cinema_id="cin-1",
        start_date=datetime(2026, 6, 30, tzinfo=UTC),
        end_date=datetime(2026, 7, 1),
    )
