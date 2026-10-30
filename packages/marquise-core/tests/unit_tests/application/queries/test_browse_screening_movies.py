"""Movie-first query bounds and clock tests."""

from datetime import UTC, date, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.application.repositories.page import Page


@pytest.mark.asyncio
async def test_montreal_dst_window_and_single_clock() -> None:
    """The autumn transition includes both repeated hours and reads the clock once."""
    reader = create_autospec(ScreeningMovieReader, instance=True)
    reader.search.return_value = Page(items=[], total=27)
    now = datetime(2026, 11, 1, 4, tzinfo=UTC)
    clock = Mock(return_value=now)
    result = await BrowseScreeningMoviesQuery(reader, clock).execute(
        BrowseScreeningMoviesQuery.InputData(date(2026, 11, 1), date(2026, 11, 1), 2)
    )
    reader.search.assert_awaited_once_with(
        datetime(2026, 11, 1, 4, tzinfo=UTC),
        datetime(2026, 11, 2, 4, 59, 59, 999999, tzinfo=UTC),
        now,
        2,
    )
    clock.assert_called_once_with()
    assert result.movies == ()
    assert result.total == 27


@pytest.mark.parametrize(
    "start,end,page",
    [
        (date(2026, 11, 2), date(2026, 11, 1), 1),
        (date(2026, 11, 1), date(2026, 11, 1), 0),
        (date(2026, 11, 1), date.max, 1),
    ],
)
def test_invalid_request(start: date, end: date, page: int) -> None:
    """Invalid ranges and pagination fail before reading storage."""
    with pytest.raises(ValueError):
        BrowseScreeningMoviesQuery.InputData(start, end, page)
