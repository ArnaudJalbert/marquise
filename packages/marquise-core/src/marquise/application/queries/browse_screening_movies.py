"""Browse distinct movies that have upcoming screenings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader


class BrowseScreeningMoviesQuery:
    """Read one movie page using one clock instant for eligibility and previews."""

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

        ranges: tuple[BrowseScreeningMoviesQuery.HourRange, ...]
        excluded: bool = False

        def __post_init__(self) -> None:
            """Require at least one range when an hour filter exists."""
            if not self.ranges:
                raise ValueError("hours must include at least one range")

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
        hours: BrowseScreeningMoviesQuery.HourFilter | None = None
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
        """Convert local date bounds and read one movie page."""
        zone = ZoneInfo("America/Montreal")
        start = datetime.combine(input_data.start, time.min, zone).astimezone(UTC)
        end = (
            datetime.combine(
                input_data.end + timedelta(days=1), time.min, zone
            ).astimezone(UTC)
            - timedelta(microseconds=1)
            if input_data.end is not None
            else None
        )
        now = self._clock()
        hours = input_data.hours
        page = await self._reader.search(
            ScreeningMovieReader.SearchRequest(
                start=start,
                end=end,
                now=now,
                page=input_data.page,
                title=input_data.title,
                cinemas=input_data.cinemas,
                languages=input_data.languages,
                hours=ScreeningMovieReader.HourFilter(
                    ranges=tuple(
                        ScreeningMovieReader.HourRange(item.start, item.end)
                        for item in hours.ranges
                    ),
                    excluded=hours.excluded,
                )
                if hours
                else None,
                excluded_cinemas=input_data.excluded_cinemas,
            )
        )
        return self.OutputData(movies=tuple(page.items), total=page.total)
