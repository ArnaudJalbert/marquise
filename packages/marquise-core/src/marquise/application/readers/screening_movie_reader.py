"""Movie-first read port for upcoming screening cards."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time

from marquise.application.readers.screening_reader import ScreeningReader
from marquise.application.repositories.page import Page


class ScreeningMovieReader(ABC):
    """Read distinct movies with their earliest qualifying screenings."""

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

    @abstractmethod
    async def search(
        self,
        start: datetime,
        end: datetime,
        now: datetime,
        page: int,
        title: str | None = None,
        cinemas: tuple[str, ...] = (),
        languages: tuple[str, ...] = (),
        start_time: time | None = None,
        end_time: time | None = None,
    ) -> Page[MovieData]:
        """Return a 24-movie page within inclusive bounds, strictly after now."""
        ...
