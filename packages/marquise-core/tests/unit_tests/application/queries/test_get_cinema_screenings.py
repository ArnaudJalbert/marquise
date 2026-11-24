"""Tests for GetCinemaScreeningsQuery."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.page import Page
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import CinemaRepository
from marquise.domain.value_objects import CinemaId


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
    cinema_repository: CinemaRepository, reader: ScreeningReader
) -> GetCinemaScreeningsQuery:
    return GetCinemaScreeningsQuery(
        cinema_repository=cinema_repository, screening_reader=reader
    )


@pytest.mark.asyncio
async def test_returns_reader_summaries() -> None:
    """Existing cinema returns reader summaries without entity construction."""
    cinema_repository = create_autospec(CinemaRepository, instance=True)
    cinema_repository.exists_by_id.return_value = True
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[_summary()], total=1)

    result = await _query(cinema_repository, reader).execute(
        GetCinemaScreeningsQuery.InputData(cinema_id="cin-1", size=10, page=1)
    )

    assert result.screenings == (_summary(),)
    assert result.total == 1
    reader.search.assert_awaited_once_with(cinema_id="cin-1", limit=10, offset=0)


@pytest.mark.asyncio
async def test_passes_page_and_size_as_limit_offset() -> None:
    """Page 2 with size 5 becomes limit 5 and offset 5."""
    cinema_repository = create_autospec(CinemaRepository, instance=True)
    cinema_repository.exists_by_id.return_value = True
    reader = create_autospec(ScreeningReader, instance=True)
    reader.search.return_value = Page(items=[], total=50)

    result = await _query(cinema_repository, reader).execute(
        GetCinemaScreeningsQuery.InputData(cinema_id="cin-1", page=2, size=5)
    )

    assert result.total == 50
    cinema_repository.exists_by_id.assert_awaited_once_with(CinemaId(value="cin-1"))
    reader.search.assert_awaited_once_with(cinema_id="cin-1", limit=5, offset=5)


@pytest.mark.asyncio
async def test_raises_when_cinema_missing() -> None:
    """Missing cinema raises before querying screening reader."""
    cinema_repository = create_autospec(CinemaRepository, instance=True)
    cinema_repository.exists_by_id.return_value = False
    reader = create_autospec(ScreeningReader, instance=True)

    with pytest.raises(CinemaNotFoundError):
        await _query(cinema_repository, reader).execute(
            GetCinemaScreeningsQuery.InputData(cinema_id="missing", size=10, page=1)
        )

    reader.search.assert_not_awaited()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"cinema_id": "  "}, "cinema_id must not be empty"),
        ({"cinema_id": "cin-1", "page": 0}, "page must be at least 1"),
        ({"cinema_id": "cin-1", "size": 0}, "size must be positive"),
    ],
)
def test_input_rejects_invalid_values(kwargs: dict, message: str) -> None:
    """Invalid cinema query input is rejected."""
    with pytest.raises(ValueError, match=message):
        GetCinemaScreeningsQuery.InputData(**{"page": 1, "size": 10, **kwargs})
