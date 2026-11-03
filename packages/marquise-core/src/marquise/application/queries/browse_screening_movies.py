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
    class InputData:
        """Inclusive Montreal dates, open-ended without end, and a page of 24.

        ``hours`` holds half-open ``(start, end)`` Montreal hour ranges matched
        with OR; empty means any hour.
        """

        start: date
        end: date | None
        page: int = 1
        title: str | None = None
        cinemas: tuple[str, ...] = ()
        languages: tuple[str, ...] = ()
        hours: tuple[tuple[int, int], ...] = ()
        excluded_cinemas: tuple[str, ...] = ()

        def __post_init__(self) -> None:
            """Reject inverted dates, invalid pages, and empty or out-of-day hours."""
            if self.end is not None and self.start > self.end:
                raise ValueError("start must not be after end")
            if self.end == date.max:
                raise ValueError("end is outside the supported date range")
            if self.page < 1:
                raise ValueError("page must be at least 1")
            if not all(0 <= start < end <= 24 for start, end in self.hours):
                raise ValueError("hours must be ranges with 0 <= start < end <= 24")

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
        page = await self._reader.search(
            start,
            end,
            now,
            input_data.page,
            input_data.title,
            input_data.cinemas,
            input_data.languages,
            input_data.hours,
            input_data.excluded_cinemas,
        )
        return self.OutputData(movies=tuple(page.items), total=page.total)
