"""Daily screening-volume query tests through execute."""

from collections.abc import Callable
from datetime import UTC, date, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions import TooManyScreeningDaysError
from marquise.application.queries.count_screening_days import CountScreeningDaysQuery
from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.domain.value_objects import HourFilter, HourRange

NOW = datetime(2026, 10, 31, 16, tzinfo=UTC)
DAY = date(2026, 11, 3)


@pytest.fixture
def reader() -> ScreeningMovieReader:
    reader = create_autospec(ScreeningMovieReader, instance=True)
    reader.count_days.return_value = []
    return reader


@pytest.fixture
def clock() -> Callable[[], datetime]:
    return Mock(return_value=NOW)


@pytest.fixture
def query(
    reader: ScreeningMovieReader, clock: Callable[[], datetime]
) -> CountScreeningDaysQuery:
    return CountScreeningDaysQuery(reader, clock)


@pytest.mark.asyncio
async def test_every_day_has_a_total_including_zero_days(
    query: CountScreeningDaysQuery, reader: ScreeningMovieReader, clock: Mock
) -> None:
    """Days without screenings report zero, over Montréal bounds across DST."""
    reader.count_days.return_value = [
        ScreeningMovieReader.DayCount(date(2026, 11, 1), 5),
    ]

    result = await query.execute(
        query.InputData(start=date(2026, 10, 31), end=date(2026, 11, 2))
    )

    assert result.days == (
        ScreeningMovieReader.DayCount(date(2026, 10, 31), 0),
        ScreeningMovieReader.DayCount(date(2026, 11, 1), 5),
        ScreeningMovieReader.DayCount(date(2026, 11, 2), 0),
    )
    reader.count_days.assert_awaited_once_with(
        ScreeningMovieReader.DayCountRequest(
            start=datetime(2026, 10, 31, 4, tzinfo=UTC),
            end=datetime(2026, 11, 3, 4, 59, 59, 999999, tzinfo=UTC),
            now=NOW,
        )
    )
    clock.assert_called_once_with()


@pytest.mark.asyncio
async def test_filters_reach_the_reader(
    query: CountScreeningDaysQuery, reader: ScreeningMovieReader
) -> None:
    """Search, cinemas, languages, hour ranges and exclusions are all counted."""
    await query.execute(
        query.InputData(
            start=date(2026, 11, 3),
            end=date(2026, 11, 3),
            title=" Dune ",
            cinemas=("c1",),
            languages=("VO",),
            hours=HourFilter(
                ranges=(HourRange(0, 17), HourRange(21, 24)),
                excluded=True,
            ),
            excluded_cinemas=("c3",),
        )
    )

    request = reader.count_days.await_args.args[0]
    assert (request.title, request.cinemas, request.languages) == (
        " Dune ",
        ("c1",),
        ("VO",),
    )
    assert request.hours == HourFilter(
        ranges=(
            HourRange(0, 17),
            HourRange(21, 24),
        ),
        excluded=True,
    )
    assert request.excluded_cinemas == ("c3",)


@pytest.mark.asyncio
async def test_a_horizon_longer_than_six_weeks_is_rejected(
    query: CountScreeningDaysQuery, reader: ScreeningMovieReader
) -> None:
    """One request stays bounded to the 42-day strip horizon."""
    await query.execute(query.InputData(date(2026, 11, 1), date(2026, 12, 12)))

    with pytest.raises(TooManyScreeningDaysError):
        await query.execute(query.InputData(date(2026, 11, 1), date(2026, 12, 13)))

    reader.count_days.assert_awaited_once()


@pytest.mark.parametrize(
    "start,end",
    [(date(2026, 11, 2), date(2026, 11, 1)), (date(2026, 11, 1), date.max)],
)
def test_invalid_date_range(start: date, end: date) -> None:
    """Inverted or unsupported dates fail before reading storage."""
    with pytest.raises(ValueError):
        CountScreeningDaysQuery.InputData(start, end)


@pytest.mark.parametrize("hours", [(21, 17), (17, 17), (-1, 5), (0, 25)])
def test_invalid_hour_range(hours: tuple[int, int]) -> None:
    """An empty, inverted or out-of-day hour range is rejected."""
    with pytest.raises(ValueError, match="hours"):
        CountScreeningDaysQuery.InputData(
            DAY, DAY, hours=HourFilter(ranges=(HourRange(*hours),))
        )


def test_empty_hour_filter() -> None:
    """An hour filter must name at least one range."""
    with pytest.raises(ValueError, match="hours"):
        CountScreeningDaysQuery.InputData(DAY, DAY, hours=HourFilter(ranges=()))


@pytest.mark.parametrize("hours", [("0", 17), (0, 17.0)])
def test_hour_range_types_are_checked(hours: tuple) -> None:
    """A non-integer hour bound fails where it enters the application."""
    with pytest.raises(TypeError, match="must be int"):
        CountScreeningDaysQuery.InputData(
            DAY, DAY, hours=HourFilter(ranges=(HourRange(*hours),))
        )


@pytest.mark.parametrize(
    "fields",
    [
        {"ranges": [HourRange(0, 17)]},
        {"ranges": (HourRange(0, 17),), "excluded": 1},
    ],
)
def test_hour_filter_types_are_checked(fields: dict) -> None:
    """Hour ranges must be a tuple and the exclusion flag a bool."""
    with pytest.raises(TypeError):
        CountScreeningDaysQuery.InputData(DAY, DAY, hours=HourFilter(**fields))


@pytest.mark.parametrize(
    "fields",
    [
        {"start": "2026-11-01"},
        {"title": 3},
        {"cinemas": ["c1"]},
        {"languages": ["VO"]},
        {"hours": (17, 21)},
        {"excluded_cinemas": ["c3"]},
    ],
)
def test_input_types_are_checked(fields: dict) -> None:
    """Wrongly typed input fails where it enters the application."""
    values = {"start": date(2026, 11, 1), "end": date(2026, 11, 1), **fields}
    with pytest.raises(TypeError):
        CountScreeningDaysQuery.InputData(**values)
