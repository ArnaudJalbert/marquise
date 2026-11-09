"""Movie-first read port for upcoming screening cards and their daily volume."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from marquise.application.readers.screening_reader import ScreeningReader
from marquise.application.repositories.page import Page


class ScreeningMovieReader(ABC):
    """Read upcoming screenings under the listing filters, by movie or by day."""

    @dataclass(frozen=True, slots=True)
    class HourRange:
        """One half-open whole-hour Montréal range."""

        start: int
        end: int

    @dataclass(frozen=True, slots=True)
    class HourFilter:
        """Hour ranges matched together before optional exclusion."""

        ranges: tuple[ScreeningMovieReader.HourRange, ...]
        excluded: bool = False

    @dataclass(frozen=True, slots=True)
    class SearchRequest:
        """All bounds and filters for one movie-first page."""

        start: datetime
        end: datetime | None
        now: datetime
        page: int
        title: str | None = None
        cinemas: tuple[str, ...] = ()
        languages: tuple[str, ...] = ()
        hours: ScreeningMovieReader.HourFilter | None = None
        excluded_cinemas: tuple[str, ...] = ()

    @dataclass(frozen=True, slots=True)
    class DayCountRequest:
        """The listing's bounds and filters, without pagination."""

        start: datetime
        end: datetime
        now: datetime
        title: str | None = None
        cinemas: tuple[str, ...] = ()
        languages: tuple[str, ...] = ()
        hours: ScreeningMovieReader.HourFilter | None = None
        excluded_cinemas: tuple[str, ...] = ()

    @dataclass(frozen=True, slots=True)
    class DayCount:
        """Matching screening occurrences on one Montréal date."""

        date: date
        screenings: int

    @dataclass(frozen=True, slots=True)
    class MovieData:
        """Movie metadata and up to three qualifying screenings in order."""

        id: str
        title: str
        release_year: int | None
        directors: tuple[str, ...] | None
        duration_minutes: int | None
        description: str | None
        poster_url: str | None
        screenings: tuple[ScreeningReader.ScreeningData, ...]
        tmdb_rating: float | None = None
        tmdb_vote_count: int | None = None

    @abstractmethod
    async def search(self, request: SearchRequest) -> Page[MovieData]:
        """Return a 24-movie page within inclusive bounds, strictly after now."""
        ...

    @abstractmethod
    async def count_days(self, request: DayCountRequest) -> list[DayCount]:
        """Count matching screenings per Montréal date, omitting empty dates."""
        ...
