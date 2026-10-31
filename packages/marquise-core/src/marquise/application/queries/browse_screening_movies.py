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
        title: str | None = None
        cinemas: tuple[str, ...] = ()
        languages: tuple[str, ...] = ()
        start_hour: int | None = None
        end_hour: int | None = None

        def __post_init__(self) -> None:
            """Reject inverted dates and invalid pages."""
            if self.start > self.end:
                raise ValueError("start must not be after end")
            if self.end == date.max:
                raise ValueError("end is outside the supported date range")
            if self.page < 1:
                raise ValueError("page must be at least 1")
            if self.start_hour is not None and not 0 <= self.start_hour <= 23:
                raise ValueError("start_hour must be between 0 and 23")
            if self.end_hour is not None and not 0 <= self.end_hour <= 24:
                raise ValueError("end_hour must be between 0 and 24")
            start_hour = self.start_hour or 0
            end_hour = self.end_hour or 24
            if start_hour > end_hour:
                raise ValueError("start_hour must not be after end_hour")

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
        page = await self._reader.search(
            start,
            end,
            now,
            request.page,
            request.title,
            request.cinemas,
            request.languages,
            time(request.start_hour) if request.start_hour not in (None, 0) else None,
            time(request.end_hour)
            if request.end_hour is not None and request.end_hour < 24
            else None,
        )
        return self.OutputData(movies=tuple(page.items), total=page.total)
