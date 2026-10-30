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
        """Inclusive Montreal dates and a one-based page of 24 movies."""

        start: date
        end: date
        page: int = 1

        def __post_init__(self) -> None:
            """Reject inverted dates and invalid pages."""
            if self.start > self.end:
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

    async def execute(self, request: InputData) -> OutputData:
        """Convert local date bounds and read one bounded movie page."""
        zone = ZoneInfo("America/Montreal")
        start = datetime.combine(request.start, time.min, zone).astimezone(UTC)
        end = datetime.combine(
            request.end + timedelta(days=1), time.min, zone
        ).astimezone(UTC) - timedelta(microseconds=1)
        now = self._clock()
        page = await self._reader.search(start, end, now, request.page)
        return self.OutputData(movies=tuple(page.items), total=page.total)
