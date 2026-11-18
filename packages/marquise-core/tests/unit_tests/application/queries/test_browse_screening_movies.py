"""Movie-first query bounds and clock tests."""

from datetime import UTC, date, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.application.repositories.page import Page
from marquise.domain import value_objects

NOW = datetime(2026, 11, 3, 18, tzinfo=UTC)
DAY = date(2026, 11, 3)


@pytest.fixture
def reader() -> ScreeningMovieReader:
    return create_autospec(ScreeningMovieReader, instance=True)


@pytest.fixture
def clock() -> Mock:
    return Mock(return_value=NOW)


@pytest.fixture
def query(reader: ScreeningMovieReader, clock: Mock) -> BrowseScreeningMoviesQuery:
    return BrowseScreeningMoviesQuery(reader, clock)


@pytest.mark.asyncio
async def test_montreal_dst_window_and_single_clock() -> None:
    """The autumn transition includes both repeated hours and reads the clock once."""
    reader = create_autospec(ScreeningMovieReader, instance=True)
    reader.search.return_value = Page(items=[], total=27)
    now = datetime(2026, 11, 1, 4, tzinfo=UTC)
    clock = Mock(return_value=now)
    result = await BrowseScreeningMoviesQuery(reader, clock).execute(
        BrowseScreeningMoviesQuery.InputData(
            date(2026, 11, 1), date(2026, 11, 1), size=24, page=2
        )
    )
    reader.search.assert_awaited_once_with(
        ScreeningMovieReader.SearchRequest(
            start=datetime(2026, 11, 1, 4, tzinfo=UTC),
            end=datetime(2026, 11, 2, 4, 59, 59, 999999, tzinfo=UTC),
            now=now,
            page=2,
            size=24,
        )
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
        BrowseScreeningMoviesQuery.InputData(start, end, size=24, page=page)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ranges", [((21, 17),), ((17, 17),), ((-1, 5),), ((0, 25),), ()]
)
async def test_invalid_hours_are_rejected_before_reading(
    query: BrowseScreeningMoviesQuery,
    reader: ScreeningMovieReader,
    clock: Mock,
    ranges: tuple[tuple[int, int], ...],
) -> None:
    """An empty filter or an inverted or out-of-day range never reaches storage."""
    hours = BrowseScreeningMoviesQuery.HourFilterInput(
        ranges=tuple(
            BrowseScreeningMoviesQuery.HourRangeInput(*item) for item in ranges
        )
    )

    with pytest.raises(ValueError, match="hours"):
        await query.execute(
            BrowseScreeningMoviesQuery.InputData(DAY, DAY, size=24, hours=hours)
        )

    clock.assert_not_called()
    reader.search.assert_not_awaited()


@pytest.mark.parametrize("hours", [("0", 17), (0, 17.0)])
def test_hour_range_types_are_checked(hours: tuple) -> None:
    """A non-integer hour bound fails where it enters the application."""
    with pytest.raises(TypeError, match="must be int"):
        BrowseScreeningMoviesQuery.HourRangeInput(*hours)


@pytest.mark.parametrize(
    "fields",
    [
        {"ranges": [BrowseScreeningMoviesQuery.HourRangeInput(0, 17)]},
        {"ranges": (BrowseScreeningMoviesQuery.HourRangeInput(0, 17),), "excluded": 1},
    ],
)
def test_hour_filter_types_are_checked(fields: dict) -> None:
    """Hour ranges must be a tuple and the exclusion flag a bool."""
    with pytest.raises(TypeError):
        BrowseScreeningMoviesQuery.HourFilterInput(**fields)


@pytest.mark.asyncio
async def test_filter_values_are_passed_to_the_reader() -> None:
    """One movie query receives every selected filter, hour range and exclusion."""
    reader = create_autospec(ScreeningMovieReader, instance=True)
    reader.search.return_value = Page(items=[], total=0)
    now = datetime(2026, 11, 3, 18, tzinfo=UTC)
    request = BrowseScreeningMoviesQuery.InputData(
        date(2026, 11, 3),
        date(2026, 11, 5),
        size=24,
        title=" Dune ",
        cinemas=("c1", "c2"),
        languages=("VO", "VOSTF"),
        hours=BrowseScreeningMoviesQuery.HourFilterInput(
            ranges=(BrowseScreeningMoviesQuery.HourRangeInput(start=17, end=21),),
            excluded=True,
        ),
        excluded_cinemas=("c3",),
    )

    await BrowseScreeningMoviesQuery(reader, Mock(return_value=now)).execute(request)

    reader.search.assert_awaited_once_with(
        ScreeningMovieReader.SearchRequest(
            start=datetime(2026, 11, 3, 5, tzinfo=UTC),
            end=datetime(2026, 11, 6, 4, 59, 59, 999999, tzinfo=UTC),
            now=now,
            page=1,
            size=24,
            title=" Dune ",
            cinemas=("c1", "c2"),
            languages=("VO", "VOSTF"),
            hours=value_objects.HourFilter(
                ranges=(value_objects.HourRange(start=17, end=21),),
                excluded=True,
            ),
            excluded_cinemas=("c3",),
        )
    )
