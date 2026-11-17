"""Browse distinct movies that have upcoming screenings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.domain.constants import MONTREAL_TIME_ZONE
from marquise.domain.value_objects import HourFilter, HourRange


class BrowseScreeningMoviesQuery:
    """Read one movie page using one clock instant for eligibility and previews."""

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

        ranges: tuple[BrowseScreeningMoviesQuery.HourRangeInput, ...]
        excluded: bool = False

        def __post_init__(self) -> None:
            """Check field types."""
            if not isinstance(self.ranges, tuple):
                raise TypeError("ranges must be a tuple")
            if not isinstance(self.excluded, bool):
                raise TypeError("excluded must be a bool")

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Inclusive Montreal dates, open-ended without end, and a page of 24.

        ``hours`` holds named Montréal ranges matched with OR before optional
        exclusion. No hour filter means any hour.
        """

        start: date
        end: date | None
        page: int = 1
        title: str | None = None
        cinemas: tuple[str, ...] = ()
        languages: tuple[str, ...] = ()
        hours: BrowseScreeningMoviesQuery.HourFilterInput | None = None
        excluded_cinemas: tuple[str, ...] = ()

        def __post_init__(self) -> None:
            """Reject inverted dates, invalid pages, and empty or out-of-day hours."""
            if self.end is not None and self.start > self.end:
                raise ValueError("start must not be after end")
            if self.end == date.max:
                raise ValueError("end is outside the supported date range")
            if self.page < 1:
                raise ValueError("page must be at least 1")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Matching movie cards and the authoritative distinct-movie total."""

        movies: tuple[ScreeningMovieReader.MovieData, ...]
        total: int

    def __init__(
        self, reader: ScreeningMovieReader, clock: Callable[[], datetime]
    ) -> None:
        """Inject the movie reader and an aware UTC clock."""
        self._reader = reader
        self._clock = clock

    async def execute(self, input_data: InputData) -> OutputData:
        """Convert local date bounds and read one movie page.

        Args:
            input_data: The inclusive Montréal dates, page and listing filters.

        Returns:
            The page's movie cards and the distinct-movie total.

        Raises:
            ValueError: If the hour filter has no range, or a range is empty,
                inverted or outside the day.
        """
        hours = (
            None if input_data.hours is None else self._to_hour_filter(input_data.hours)
        )
        start = datetime.combine(
            input_data.start, time.min, MONTREAL_TIME_ZONE
        ).astimezone(UTC)
        end = (
            datetime.combine(
                input_data.end + timedelta(days=1), time.min, MONTREAL_TIME_ZONE
            ).astimezone(UTC)
            - timedelta(microseconds=1)
            if input_data.end is not None
            else None
        )
        now = self._clock()
        page = await self._reader.search(
            ScreeningMovieReader.SearchRequest(
                start=start,
                end=end,
                now=now,
                page=input_data.page,
                title=input_data.title,
                cinemas=input_data.cinemas,
                languages=input_data.languages,
                hours=hours,
                excluded_cinemas=input_data.excluded_cinemas,
            )
        )
        return self.OutputData(movies=tuple(page.items), total=page.total)

    @staticmethod
    def _to_hour_filter(
        hours: BrowseScreeningMoviesQuery.HourFilterInput,
    ) -> HourFilter:
        ranges = tuple(HourRange(item.start, item.end) for item in hours.ranges)
        return HourFilter(ranges=ranges, excluded=hours.excluded)
