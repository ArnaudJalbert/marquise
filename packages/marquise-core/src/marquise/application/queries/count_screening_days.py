"""Count upcoming screenings on each Montréal date of a bounded horizon."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from marquise.application.exceptions import TooManyScreeningDaysError
from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.domain.constants import MONTREAL_TIME_ZONE
from marquise.domain.value_objects import HourFilter, HourRange

logger = logging.getLogger(__name__)


class CountScreeningDaysQuery:
    """Total the listing's matching screenings per day, with zero for empty days."""

    _MAX_DAYS = 42

    @dataclass(frozen=True, slots=True)
    class HourRangeInput:
        """One half-open whole-hour Montréal range."""

        start: int
        end: int

        def __post_init__(self) -> None:
            """Check field types."""
            if not isinstance(self.start, int) or not isinstance(self.end, int):
                raise TypeError("start and end must be int")

    @dataclass(frozen=True, slots=True)
    class HourFilterInput:
        """Hour ranges matched together before optional exclusion."""

        ranges: tuple[CountScreeningDaysQuery.HourRangeInput, ...]
        excluded: bool = False

        def __post_init__(self) -> None:
            """Check field types."""
            if not isinstance(self.ranges, tuple):
                raise TypeError("ranges must be a tuple")
            if not isinstance(self.excluded, bool):
                raise TypeError("excluded must be a bool")

    @dataclass(frozen=True, slots=True)
    class InputData:
        """An inclusive Montréal horizon and the listing's non-date filters."""

        start: date
        end: date
        title: str | None = None
        cinemas: tuple[str, ...] = ()
        languages: tuple[str, ...] = ()
        hours: CountScreeningDaysQuery.HourFilterInput | None = None
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
                self.hours, CountScreeningDaysQuery.HourFilterInput
            ):
                raise TypeError("hours must be an HourFilterInput")
            self._require_valid_dates(self.start, self.end)

        @staticmethod
        def _require_valid_dates(start: date, end: date) -> None:
            """Reject an inverted horizon or an end with no following day."""
            if start > end:
                raise ValueError("start must not be after end")
            if end == date.max:
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
            ValueError: If the hour filter has no range, or a range is empty,
                inverted or outside the day.
        """
        self._require_bounded_horizon(input_data.start, input_data.end)
        hours = (
            None if input_data.hours is None else self._to_hour_filter(input_data.hours)
        )
        request = self._to_day_count_request(input_data, hours)
        counts = await self._reader.count_days(request)
        days = self._fill_missing_days(input_data.start, input_data.end, counts)
        logger.info("Counted screenings on %d days", len(days))
        return self.OutputData(days=days)

    @staticmethod
    def _to_hour_filter(
        hours: CountScreeningDaysQuery.HourFilterInput,
    ) -> HourFilter:
        ranges = tuple(HourRange(item.start, item.end) for item in hours.ranges)
        return HourFilter(ranges=ranges, excluded=hours.excluded)

    def _to_day_count_request(
        self, input_data: InputData, hours: HourFilter | None
    ) -> ScreeningMovieReader.DayCountRequest:
        return ScreeningMovieReader.DayCountRequest(
            start=self._to_utc_day_start(input_data.start),
            end=self._to_utc_day_end(input_data.end),
            now=self._clock(),
            title=input_data.title,
            cinemas=input_data.cinemas,
            languages=input_data.languages,
            hours=hours,
            excluded_cinemas=input_data.excluded_cinemas,
        )

    def _require_bounded_horizon(self, start: date, end: date) -> None:
        if (end - start).days + 1 > self._MAX_DAYS:
            raise TooManyScreeningDaysError(
                f"A count covers at most {self._MAX_DAYS} days"
            )

    def _to_utc_day_end(self, day: date) -> datetime:
        next_day_start = self._to_utc_day_start(day + timedelta(days=1))
        return next_day_start - timedelta(microseconds=1)

    def _to_utc_day_start(self, day: date) -> datetime:
        return datetime.combine(day, time.min, MONTREAL_TIME_ZONE).astimezone(UTC)

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
