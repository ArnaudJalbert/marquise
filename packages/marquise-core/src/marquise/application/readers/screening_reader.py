"""Read port for screening display data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from marquise.application.page import Page


class ScreeningReader(ABC):
    """Read screening display data without constructing domain entities."""

    @dataclass(frozen=True, slots=True)
    class ScreeningData:
        """Display data for one screening."""

        id: str
        movie_id: str
        movie_title: str
        cinema_id: str
        cinema_name: str
        showtime: datetime
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

    @abstractmethod
    async def find_by_id(self, screening_id: str) -> ScreeningData | None:
        """Return one screening projection, or None when its ID is missing."""
        ...

    @abstractmethod
    async def search(
        self,
        movie_id: str | None = None,
        movie_title: str | None = None,
        cinema_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        language: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[ScreeningReader.ScreeningData]:
        """Return screenings matching optional filters, paginated."""
        ...
