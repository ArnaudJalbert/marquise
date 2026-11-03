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
        None,
        (),
        (),
        (),
        (),
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


@pytest.mark.parametrize("hours", [(21, 17), (17, 17), (-1, 5), (0, 25)])
def test_invalid_hour_range(hours: tuple[int, int]) -> None:
    """An empty, inverted or out-of-day range is rejected even beside a valid one."""
    with pytest.raises(ValueError, match="hours"):
        BrowseScreeningMoviesQuery.InputData(
            date(2026, 11, 1), None, hours=((0, 24), hours)
        )


@pytest.mark.asyncio
async def test_filter_values_are_passed_to_the_reader() -> None:
    """One movie query receives every selected filter, hour range and exclusion."""
    reader = create_autospec(ScreeningMovieReader, instance=True)
    reader.search.return_value = Page(items=[], total=0)
    now = datetime(2026, 11, 3, 18, tzinfo=UTC)
    request = BrowseScreeningMoviesQuery.InputData(
        date(2026, 11, 3),
        date(2026, 11, 5),
        title=" Dune ",
        cinemas=("c1", "c2"),
        languages=("VO", "VOSTF"),
        hours=((0, 17), (21, 24)),
        excluded_cinemas=("c3",),
    )

    await BrowseScreeningMoviesQuery(reader, Mock(return_value=now)).execute(request)

    reader.search.assert_awaited_once()
    assert reader.search.call_args.args[4:] == (
        " Dune ",
        ("c1", "c2"),
        ("VO", "VOSTF"),
        ((0, 17), (21, 24)),
        ("c3",),
    )
