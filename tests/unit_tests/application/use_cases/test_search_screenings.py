"""Tests for SearchScreeningsUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import Page, ScreeningRepository
from marquise.application.use_cases.search_screenings import SearchScreeningsUseCase
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)


def _screening() -> Screening:
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    movie = Movie(id=MovieId(value="mov-1"), title="The Odyssey")
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=movie,
        cinema=cinema,
        showtime=Showtime(value=datetime(2026, 6, 27, 19, 30, tzinfo=UTC)),
    )


@pytest.mark.asyncio
async def test_returns_matching_screenings() -> None:
    """The use case returns the screenings from the repository, mapped."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[_screening()], total=1)

    use_case = SearchScreeningsUseCase(screening_repository=screening_repo)
    result = await use_case.execute(SearchScreeningsUseCase.InputData())

    assert len(result.screenings) == 1
    assert result.screenings[0].movie_title == "The Odyssey"
    assert result.screenings[0].showtime.startswith("2026-06-27T19:30")
    assert result.total == 1


@pytest.mark.asyncio
async def test_passes_all_filters_to_repository() -> None:
    """All provided filters are converted to value objects and forwarded."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[], total=0)

    use_case = SearchScreeningsUseCase(screening_repository=screening_repo)
    request = SearchScreeningsUseCase.InputData(
        movie="Odyssey",
        movie_id="mov-1",
        cinema_id="cin-1",
        start_date=datetime(2026, 6, 27, tzinfo=UTC),
        end_date=datetime(2026, 6, 28, tzinfo=UTC),
        language="V.O.",
    )
    await use_case.execute(request)

    screening_repo.search.assert_awaited_once_with(
        movie_id=MovieId(value="mov-1"),
        movie_title="Odyssey",
        cinema_id=CinemaId(value="cin-1"),
        start_date=request.start_date,
        end_date=request.end_date,
        language="V.O.",
        limit=None,
        offset=0,
    )


@pytest.mark.asyncio
async def test_passes_page_and_size_to_repository_as_limit_offset() -> None:
    """page/size from the input are converted to limit/offset for the repository.

    Page 2, size 5 should produce limit=5, offset=5.
    """
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[], total=50)

    use_case = SearchScreeningsUseCase(screening_repository=screening_repo)
    result = await use_case.execute(SearchScreeningsUseCase.InputData(page=2, size=5))

    screening_repo.search.assert_awaited_once_with(
        movie_id=None,
        movie_title=None,
        cinema_id=None,
        start_date=None,
        end_date=None,
        language=None,
        limit=5,
        offset=5,
    )
    assert result.total == 50


def test_input_rejects_page_below_one() -> None:
    """A page less than 1 is rejected."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        SearchScreeningsUseCase.InputData(page=0)


def test_input_rejects_non_positive_size() -> None:
    """A non-positive size is rejected when provided."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        SearchScreeningsUseCase.InputData(size=0)


def test_input_rejects_inverted_range() -> None:
    """start_date after end_date is rejected."""
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        SearchScreeningsUseCase.InputData(
            start_date=datetime(2026, 6, 28, tzinfo=UTC),
            end_date=datetime(2026, 6, 27, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("movie", "  "),
        ("movie_id", "  "),
        ("cinema_id", "  "),
        ("language", "  "),
    ],
)
def test_input_rejects_blank_string_filters(field: str, value: str) -> None:
    """Whitespace-only string filters are rejected."""
    with pytest.raises(ValueError, match="must not be empty when provided"):
        SearchScreeningsUseCase.InputData(**{field: value})
