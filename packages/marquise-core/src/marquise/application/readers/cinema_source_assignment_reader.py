"""Read port for cinema-source assignment display data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class CinemaSourceAssignmentReader(ABC):
    """Read cinema-source assignments without constructing domain entities."""

    @dataclass(frozen=True, slots=True)
    class CinemaSourceAssignmentData:
        """Display data for one cinema-source assignment."""

        cinema_id: str
        source_name: str
        source_display_name: str

    @abstractmethod
    async def list_all(self) -> list[CinemaSourceAssignmentData]:
        """Return every cinema-source assignment's display data."""
        ...

    @abstractmethod
    async def find_by_cinema_id(
        self, cinema_id: str
    ) -> CinemaSourceAssignmentData | None:
        """Return one cinema's assignment, or None when it has no source."""
        ...
