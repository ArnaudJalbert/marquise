"""Tests for GetMovieScreeningsUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.repositories import (
    MovieRepository,
    Page,
    ScreeningRepository,
)
from marquise.application.use_cases.get_movie_screenings import (
    GetMovieScreeningsUseCase,
)
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)


def _input() -> GetMovieScreeningsUseCase.InputData:
    return GetMovieScreeningsUseCase.InputData(
        movie_id="mov-1",
        start_date=datetime(2026, 6, 27, tzinfo=UTC),
        end_date=datetime(2026, 6, 28, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_returns_movie_and_screenings() -> None:
    """The use case returns the movie with its screenings."""
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    movie = Movie(id=MovieId(value="mov-1"), title="The Odyssey")
    screening = Screening(
        id=ScreeningId(value="scr-1"),
        movie=movie,
        cinema=cinema,
        showtime=Showtime(value=datetime(2026, 6, 27, 19, 30, tzinfo=UTC)),
    )
    movie_repo = create_autospec(MovieRepository, instance=True)
    movie_repo.find_by_id.return_value = movie
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[screening], total=1)

    use_case = GetMovieScreeningsUseCase(
        movie_repository=movie_repo,
        screening_repository=screening_repo,
    )
    result = await use_case.execute(_input())

    assert result.movie_title == "The Odyssey"
    assert len(result.screenings) == 1
    assert result.screenings[0].movie_title == "The Odyssey"
    assert result.screenings[0].cinema_id == "cin-1"
    assert result.screenings[0].cinema_name == "Cinema One"
    assert result.total == 1


@pytest.mark.asyncio
async def test_passes_filters_and_pagination_to_repository() -> None:
    """cinema_id/language filters and page/size are converted and forwarded."""
    movie = Movie(id=MovieId(value="mov-1"), title="The Odyssey")
    movie_repo = create_autospec(MovieRepository, instance=True)
    movie_repo.find_by_id.return_value = movie
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[], total=50)

    use_case = GetMovieScreeningsUseCase(
        movie_repository=movie_repo,
        screening_repository=screening_repo,
    )
    request = GetMovieScreeningsUseCase.InputData(
        movie_id="mov-1",
        start_date=datetime(2026, 6, 27, tzinfo=UTC),
        end_date=datetime(2026, 6, 28, tzinfo=UTC),
        cinema_id="cin-1",
        language="V.O.",
        page=2,
        size=5,
    )
    result = await use_case.execute(request)

    screening_repo.search.assert_awaited_once_with(
        movie_id=MovieId(value="mov-1"),
        cinema_id=CinemaId(value="cin-1"),
        start_date=request.start_date,
        end_date=request.end_date,
        language="V.O.",
        limit=5,
        offset=5,
    )
    assert result.total == 50


@pytest.mark.asyncio
async def test_raises_when_movie_missing() -> None:
    """A missing movie raises MovieNotFoundError before querying screenings."""
    movie_repo = create_autospec(MovieRepository, instance=True)
    movie_repo.find_by_id.return_value = None
    screening_repo = create_autospec(ScreeningRepository, instance=True)

    use_case = GetMovieScreeningsUseCase(
        movie_repository=movie_repo,
        screening_repository=screening_repo,
    )
    with pytest.raises(MovieNotFoundError):
        await use_case.execute(_input())
    screening_repo.search.assert_not_awaited()


def test_input_rejects_page_below_one() -> None:
    """A page less than 1 is rejected."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        GetMovieScreeningsUseCase.InputData(
            movie_id="mov-1",
            start_date=datetime(2026, 6, 27, tzinfo=UTC),
            end_date=datetime(2026, 6, 28, tzinfo=UTC),
            page=0,
        )


def test_input_rejects_non_positive_size() -> None:
    """A non-positive size is rejected when provided."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        GetMovieScreeningsUseCase.InputData(
            movie_id="mov-1",
            start_date=datetime(2026, 6, 27, tzinfo=UTC),
            end_date=datetime(2026, 6, 28, tzinfo=UTC),
            size=0,
        )


def test_input_rejects_blank_cinema_id() -> None:
    """A whitespace-only cinema_id is rejected when provided."""
    with pytest.raises(ValueError, match="cinema_id must not be empty when provided"):
        GetMovieScreeningsUseCase.InputData(
            movie_id="mov-1",
            start_date=datetime(2026, 6, 27, tzinfo=UTC),
            end_date=datetime(2026, 6, 28, tzinfo=UTC),
            cinema_id="  ",
        )


def test_input_rejects_inverted_range() -> None:
    """start_date after end_date is rejected."""
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        GetMovieScreeningsUseCase.InputData(
            movie_id="mov-1",
            start_date=datetime(2026, 6, 28, tzinfo=UTC),
            end_date=datetime(2026, 6, 27, tzinfo=UTC),
        )
