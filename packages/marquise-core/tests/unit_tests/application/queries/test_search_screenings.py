"""Tests for SearchScreeningsQuery."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.page import Page
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import CinemaRepository, MovieRepository
from marquise.domain.value_objects import CinemaId, MovieId


def _summary() -> ScreeningReader.ScreeningData:
    return ScreeningReader.ScreeningData(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_returns_matching_screenings() -> None:
    """The query returns the reader's summaries as-is."""
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[_summary()], total=1)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)

    query = SearchScreeningsQuery(
        screening_reader=reader,
        cinema_repository=cinema_repo,
        movie_repository=movie_repo,
    )
    result = await query.execute(SearchScreeningsQuery.InputData(size=10, page=1))

    assert result.screenings == (
        SearchScreeningsQuery.ScreeningData(
            id="scr-1",
            movie_id="mov-1",
            movie_title="The Odyssey",
            cinema_id="cin-1",
            cinema_name="Cinema One",
            showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
        ),
    )
    assert result.total == 1


@pytest.mark.asyncio
async def test_passes_all_filters_to_reader() -> None:
    """All provided filters are forwarded to the screening reader."""
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[], total=0)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.exists_by_id.return_value = True
    movie_repo = create_autospec(MovieRepository, instance=True)
    movie_repo.exists_by_id.return_value = True
    query = SearchScreeningsQuery(
        screening_reader=reader,
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
        size=10,
        page=1,
    )

    await query.execute(request)

    reader.search.assert_awaited_once_with(
        movie_id="mov-1",
        movie_title="Odyssey",
        cinema_id="cin-1",
        start_date=request.start_date,
        end_date=request.end_date,
        language="V.O.",
        limit=10,
        offset=0,
    )
    movie_repo.exists_by_id.assert_awaited_once_with(MovieId(value="mov-1"))
    cinema_repo.exists_by_id.assert_awaited_once_with(CinemaId(value="cin-1"))


@pytest.mark.asyncio
async def test_passes_page_and_size_as_limit_offset() -> None:
    """Page 2 with size 5 becomes limit 5 and offset 5."""
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[], total=50)
    query = SearchScreeningsQuery(
        screening_reader=reader,
        cinema_repository=create_autospec(CinemaRepository, instance=True),
        movie_repository=create_autospec(MovieRepository, instance=True),
    )

    result = await query.execute(SearchScreeningsQuery.InputData(page=2, size=5))

    reader.search.assert_awaited_once_with(
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
    """A missing movie_id filter raises MovieNotFoundError before reading."""
    reader = create_autospec(ScreeningReader, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)
    movie_repo.exists_by_id.return_value = False
    query = SearchScreeningsQuery(
        screening_reader=reader,
        cinema_repository=create_autospec(CinemaRepository, instance=True),
        movie_repository=movie_repo,
    )

    with pytest.raises(MovieNotFoundError):
        await query.execute(
            SearchScreeningsQuery.InputData(movie_id="missing", size=10, page=1)
        )

    reader.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_cinema_id_filter_missing() -> None:
    """A missing cinema_id filter raises CinemaNotFoundError before reading."""
    reader = create_autospec(ScreeningReader, instance=True)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.exists_by_id.return_value = False
    query = SearchScreeningsQuery(
        screening_reader=reader,
        cinema_repository=cinema_repo,
        movie_repository=create_autospec(MovieRepository, instance=True),
    )

    with pytest.raises(CinemaNotFoundError):
        await query.execute(
            SearchScreeningsQuery.InputData(cinema_id="missing", size=10, page=1)
        )

    reader.search.assert_not_awaited()


def test_input_rejects_page_below_one() -> None:
    """A page less than 1 is rejected."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        SearchScreeningsQuery.InputData(page=0, size=10)


def test_input_rejects_non_positive_size() -> None:
    """A non-positive size is rejected."""
    with pytest.raises(ValueError, match="size must be positive"):
        SearchScreeningsQuery.InputData(size=0, page=1)


def test_input_rejects_inverted_range() -> None:
    """A start date after the end date is rejected."""
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        SearchScreeningsQuery.InputData(
            start_date=datetime(2026, 6, 28, tzinfo=UTC),
            end_date=datetime(2026, 6, 27, tzinfo=UTC),
            size=10,
            page=1,
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
        SearchScreeningsQuery.InputData(**{field: value}, size=10, page=1)
