"""Tests for SearchScreeningsQuery."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    Page,
    ScreeningRepository,
    ScreeningSummary,
)
from marquise.application.use_cases.search_screenings import SearchScreeningsQuery
from marquise.domain.value_objects import CinemaId, MovieId


def _summary() -> ScreeningSummary:
    return ScreeningSummary(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_returns_matching_screenings() -> None:
    """The query returns the repository's summaries as-is."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[_summary()], total=1)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)

    query = SearchScreeningsQuery(
        screening_repository=screening_repo,
        cinema_repository=cinema_repo,
        movie_repository=movie_repo,
    )
    result = await query.execute(SearchScreeningsQuery.InputData())

    assert len(result.screenings) == 1
    assert result.screenings[0] == _summary()
    assert result.screenings[0].movie_title == "The Odyssey"
    assert result.screenings[0].cinema_id == "cin-1"
    assert result.screenings[0].cinema_name == "Cinema One"
    assert result.screenings[0].showtime == datetime(2026, 6, 27, 19, 30, tzinfo=UTC)
    assert result.total == 1


@pytest.mark.asyncio
async def test_passes_all_filters_to_repository() -> None:
    """All provided filters are converted to value objects and forwarded."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[], total=0)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)

    query = SearchScreeningsQuery(
        screening_repository=screening_repo,
        cinema_repository=cinema_repo,
        movie_repository=movie_repo,
    )
    request = SearchScreeningsQuery.InputData(
        movie="Odyssey",
        movie_id="mov-1",
        cinema_id="cin-1",
        start_date=datetime(2026, 6, 27, tzinfo=UTC),
        end_date=datetime(2026, 6, 28, tzinfo=UTC),
        language="V.O.",
    )
    await query.execute(request)

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
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)

    query = SearchScreeningsQuery(
        screening_repository=screening_repo,
        cinema_repository=cinema_repo,
        movie_repository=movie_repo,
    )
    result = await query.execute(SearchScreeningsQuery.InputData(page=2, size=5))

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


@pytest.mark.asyncio
async def test_raises_when_movie_id_filter_missing() -> None:
    """A movie_id filter that doesn't exist raises MovieNotFoundError."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)
    movie_repo.exists_by_id.return_value = False

    query = SearchScreeningsQuery(
        screening_repository=screening_repo,
        cinema_repository=cinema_repo,
        movie_repository=movie_repo,
    )
    with pytest.raises(MovieNotFoundError):
        await query.execute(SearchScreeningsQuery.InputData(movie_id="missing"))
    screening_repo.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_cinema_id_filter_missing() -> None:
    """A cinema_id filter that doesn't exist raises CinemaNotFoundError."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.exists_by_id.return_value = False
    movie_repo = create_autospec(MovieRepository, instance=True)

    query = SearchScreeningsQuery(
        screening_repository=screening_repo,
        cinema_repository=cinema_repo,
        movie_repository=movie_repo,
    )
    with pytest.raises(CinemaNotFoundError):
        await query.execute(SearchScreeningsQuery.InputData(cinema_id="missing"))
    screening_repo.search.assert_not_awaited()


def test_input_rejects_page_below_one() -> None:
    """A page less than 1 is rejected."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        SearchScreeningsQuery.InputData(page=0)


def test_input_rejects_non_positive_size() -> None:
    """A non-positive size is rejected when provided."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        SearchScreeningsQuery.InputData(size=0)


def test_input_rejects_inverted_range() -> None:
    """start_date after end_date is rejected."""
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        SearchScreeningsQuery.InputData(
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
        SearchScreeningsQuery.InputData(**{field: value})
