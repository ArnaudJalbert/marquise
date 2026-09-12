"""Read port for screening search display data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from marquise.application.repositories.page import Page


class ScreeningReader(ABC):
    """Search screening display data without constructing domain entities."""

    @dataclass(frozen=True, slots=True)
    class ScreeningData:
        """Display data for one screening search result."""

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
