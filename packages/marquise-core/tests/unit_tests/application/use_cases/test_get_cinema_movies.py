"""Tests for GetCinemaMoviesUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.page import Page
from marquise.application.repositories import (
    CinemaRepository,
    ScreeningRepository,
)
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.domain.entities import Cinema, Movie
from marquise.domain.value_objects import CinemaId, MovieId


def _input() -> GetCinemaMoviesUseCase.InputData:
    return GetCinemaMoviesUseCase.InputData(
        cinema_id="cin-1",
        start_date=datetime(2026, 6, 27, tzinfo=UTC),
        end_date=datetime(2026, 6, 28, tzinfo=UTC),
        size=10,
        page=1,
    )


@pytest.mark.asyncio
async def test_returns_cinema_and_distinct_movies() -> None:
    """The use case returns the cinema with its distinct movies."""
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    movie = Movie(id=MovieId(value="mov-1"), title="The Odyssey")
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = cinema
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_distinct_movies_by_cinema.return_value = Page(
        items=[movie], total=1
    )

    use_case = GetCinemaMoviesUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    result = await use_case.execute(_input())

    assert result.cinema_name == "Cinema One"
    assert len(result.movies) == 1
    assert result.movies[0].title == "The Odyssey"
    assert result.total == 1


@pytest.mark.asyncio
async def test_passes_page_and_size_to_repository_as_limit_offset() -> None:
    """page/size from the input are converted to limit/offset for the repository.

    Page 2, size 5 should produce limit=5, offset=5.
    """
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = cinema
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_distinct_movies_by_cinema.return_value = Page(
        items=[], total=50
    )

    use_case = GetCinemaMoviesUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    request = GetCinemaMoviesUseCase.InputData(
        cinema_id="cin-1",
        start_date=datetime(2026, 6, 27, tzinfo=UTC),
        end_date=datetime(2026, 6, 28, tzinfo=UTC),
        page=2,
        size=5,
    )
    result = await use_case.execute(request)

    screening_repo.find_distinct_movies_by_cinema.assert_awaited_once_with(
        cinema_id=CinemaId(value="cin-1"),
        start_date=request.start_date,
        end_date=request.end_date,
        limit=5,
        offset=5,
    )
    assert result.total == 50


def test_input_rejects_page_below_one() -> None:
    """A page less than 1 is rejected."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        GetCinemaMoviesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 6, 27, tzinfo=UTC),
            end_date=datetime(2026, 6, 28, tzinfo=UTC),
            page=0,
            size=10,
        )


def test_input_rejects_non_positive_size() -> None:
    """A non-positive size is rejected."""
    with pytest.raises(ValueError, match="size must be positive"):
        GetCinemaMoviesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 6, 27, tzinfo=UTC),
            end_date=datetime(2026, 6, 28, tzinfo=UTC),
            size=0,
            page=1,
        )


@pytest.mark.parametrize(
    ("start_date", "end_date", "message"),
    [
        (
            datetime(2026, 6, 28, tzinfo=UTC),
            datetime(2026, 6, 27, tzinfo=UTC),
            "start_date must not be after end_date",
        ),
        (
            datetime(2026, 6, 27),
            datetime(2026, 6, 28, tzinfo=UTC),
            "start_date must be timezone-aware",
        ),
        (
            datetime(2026, 6, 27, tzinfo=UTC),
            datetime(2026, 6, 28),
            "end_date must be timezone-aware",
        ),
    ],
)
def test_input_rejects_invalid_range(
    start_date: datetime, end_date: datetime, message: str
) -> None:
    """Inverted ranges and either naive boundary are rejected."""
    with pytest.raises(ValueError, match=message):
        GetCinemaMoviesUseCase.InputData(
            cinema_id="cin-1",
            start_date=start_date,
            end_date=end_date,
            size=10,
            page=1,
        )


@pytest.mark.asyncio
async def test_raises_when_cinema_missing() -> None:
    """A missing cinema raises CinemaNotFoundError before querying movies."""
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.exists_by_id.return_value = False
    screening_repo = create_autospec(ScreeningRepository, instance=True)

    use_case = GetCinemaMoviesUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    with pytest.raises(CinemaNotFoundError):
        await use_case.execute(_input())
    screening_repo.find_distinct_movies_by_cinema.assert_not_awaited()
