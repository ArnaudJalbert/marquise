"""Count upcoming screenings on each Montréal date of a bounded horizon."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from marquise.application.exceptions import TooManyScreeningDaysError
from marquise.application.readers.screening_movie_reader import ScreeningMovieReader

logger = logging.getLogger(__name__)


class CountScreeningDaysQuery:
    """Total the listing's matching screenings per day, with zero for empty days."""

    _MAX_DAYS = 42
    _ZONE = ZoneInfo("America/Montreal")

    @dataclass(frozen=True, slots=True)
    class HourRange:
        """One half-open whole-hour Montréal range."""

        start: int
        end: int

        def __post_init__(self) -> None:
            """Reject empty, inverted, or out-of-day ranges."""
            if not 0 <= self.start < self.end <= 24:
                raise ValueError("hours must satisfy 0 <= start < end <= 24")

    @dataclass(frozen=True, slots=True)
    class HourFilter:
        """Hour ranges matched together before optional exclusion."""

        ranges: tuple[CountScreeningDaysQuery.HourRange, ...]
        excluded: bool = False

        def __post_init__(self) -> None:
            """Require at least one range when an hour filter exists."""
            if not self.ranges:
                raise ValueError("hours must include at least one range")

    @dataclass(frozen=True, slots=True)
    class InputData:
        """An inclusive Montréal horizon and the listing's non-date filters."""

        start: date
        end: date
        title: str | None = None
        cinemas: tuple[str, ...] = ()
        languages: tuple[str, ...] = ()
        hours: CountScreeningDaysQuery.HourFilter | None = None
        excluded_cinemas: tuple[str, ...] = ()

        def __post_init__(self) -> None:
            """Check field types, then reject inverted or unsupported dates."""
            if not isinstance(self.start, date) or not isinstance(self.end, date):
                raise TypeError("start and end must be dates")
            if self.title is not None and not isinstance(self.title, str):
                raise TypeError("title must be a string")
            for name in ("cinemas", "languages", "excluded_cinemas"):
                if not isinstance(getattr(self, name), tuple):
                    raise TypeError(f"{name} must be a tuple")
            if self.hours is not None and not isinstance(
                self.hours, CountScreeningDaysQuery.HourFilter
            ):
                raise TypeError("hours must be an HourFilter")
            if self.start > self.end:
                raise ValueError("start must not be after end")
            if self.end == date.max:
                raise ValueError("end is outside the supported date range")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """One total per horizon date, in date order."""

        days: tuple[ScreeningMovieReader.DayCount, ...]

    def __init__(
        self, reader: ScreeningMovieReader, clock: Callable[[], datetime]
    ) -> None:
        """Inject the screening reader and an aware UTC clock."""
        self._reader = reader
        self._clock = clock

    async def execute(self, input_data: InputData) -> OutputData:
        """Count matching upcoming screenings on every day of the horizon.

        Args:
            input_data: The inclusive horizon and the listing's filters.

        Returns:
            Every horizon date with its screening total, zero included.

        Raises:
            TooManyScreeningDaysError: If the horizon exceeds 42 days.
        """
        self._require_bounded_horizon(input_data.start, input_data.end)
        start, end = self._to_utc_window(input_data.start, input_data.end)
        hours = input_data.hours
        reader_hours = (
            None
            if hours is None
            else ScreeningMovieReader.HourFilter(
                ranges=tuple(
                    ScreeningMovieReader.HourRange(item.start, item.end)
                    for item in hours.ranges
                ),
                excluded=hours.excluded,
            )
        )
        counts = await self._reader.count_days(
            ScreeningMovieReader.DayCountRequest(
                start=start,
                end=end,
                now=self._clock(),
                title=input_data.title,
                cinemas=input_data.cinemas,
                languages=input_data.languages,
                hours=reader_hours,
                excluded_cinemas=input_data.excluded_cinemas,
            )
        )
        days = self._fill_missing_days(input_data.start, input_data.end, counts)
        logger.info("Counted screenings on %d days", len(days))
        return self.OutputData(days=days)

    def _require_bounded_horizon(self, start: date, end: date) -> None:
        if (end - start).days + 1 > self._MAX_DAYS:
            raise TooManyScreeningDaysError(
                f"A count covers at most {self._MAX_DAYS} days"
            )

    def _to_utc_window(self, start: date, end: date) -> tuple[datetime, datetime]:
        last_instant = self._to_utc_day_start(end + timedelta(days=1)) - timedelta(
            microseconds=1
        )
        return self._to_utc_day_start(start), last_instant

    def _to_utc_day_start(self, day: date) -> datetime:
        return datetime.combine(day, time.min, self._ZONE).astimezone(UTC)

    @staticmethod
    def _fill_missing_days(
        start: date, end: date, counts: list[ScreeningMovieReader.DayCount]
    ) -> tuple[ScreeningMovieReader.DayCount, ...]:
        totals = {count.date: count.screenings for count in counts}
        dates = (
            start + timedelta(days=offset) for offset in range((end - start).days + 1)
        )
        return tuple(
            ScreeningMovieReader.DayCount(day, totals.get(day, 0)) for day in dates
        )
