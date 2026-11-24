"""Tests for GetMovieScreeningsQuery."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.page import Page
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import MovieRepository
from marquise.domain.value_objects import MovieId


def _summary() -> ScreeningReader.ScreeningData:
    return ScreeningReader.ScreeningData(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
    )


def _query(
    movie_repository: MovieRepository, reader: ScreeningReader
) -> GetMovieScreeningsQuery:
    return GetMovieScreeningsQuery(
        movie_repository=movie_repository, screening_reader=reader
    )


@pytest.mark.asyncio
async def test_returns_reader_summaries() -> None:
    """Existing movie returns reader summaries without entity construction."""
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.exists_by_id.return_value = True
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[_summary()], total=1)

    result = await _query(movie_repository, reader).execute(
        GetMovieScreeningsQuery.InputData(movie_id="mov-1", size=10, page=1)
    )

    assert result.screenings == (_summary(),)
    assert result.total == 1
    reader.search.assert_awaited_once_with(movie_id="mov-1", limit=10, offset=0)


@pytest.mark.asyncio
async def test_passes_start_as_reader_start_date() -> None:
    """A start datetime reaches the reader search as its start date."""
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.exists_by_id.return_value = True
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[], total=0)
    start = datetime(2026, 6, 27, 18, 0, tzinfo=UTC)

    await _query(movie_repository, reader).execute(
        GetMovieScreeningsQuery.InputData(
            movie_id="mov-1", start=start, size=100, page=1
        )
    )

    reader.search.assert_awaited_once_with(
        movie_id="mov-1", start_date=start, limit=100, offset=0
    )


@pytest.mark.asyncio
async def test_passes_page_and_size_as_limit_offset() -> None:
    """Page 2 with size 5 becomes limit 5 and offset 5."""
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.exists_by_id.return_value = True
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[], total=50)

    result = await _query(movie_repository, reader).execute(
        GetMovieScreeningsQuery.InputData(movie_id="mov-1", page=2, size=5)
    )

    assert result.total == 50
    movie_repository.exists_by_id.assert_awaited_once_with(MovieId(value="mov-1"))
    reader.search.assert_awaited_once_with(movie_id="mov-1", limit=5, offset=5)


@pytest.mark.asyncio
async def test_raises_when_movie_missing() -> None:
    """Missing movie raises before querying screening reader."""
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.exists_by_id.return_value = False
    reader = create_autospec(ScreeningReader, instance=True)

    with pytest.raises(MovieNotFoundError):
        await _query(movie_repository, reader).execute(
            GetMovieScreeningsQuery.InputData(movie_id="missing", size=10, page=1)
        )

    reader.search.assert_not_awaited()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"movie_id": "  "}, "movie_id must not be empty"),
        ({"movie_id": "mov-1", "page": 0}, "page must be at least 1"),
        ({"movie_id": "mov-1", "size": 0}, "size must be positive"),
    ],
)
def test_input_rejects_invalid_values(kwargs: dict, message: str) -> None:
    """Invalid movie query input is rejected."""
    with pytest.raises(ValueError, match=message):
        GetMovieScreeningsQuery.InputData(**{"page": 1, "size": 10, **kwargs})
