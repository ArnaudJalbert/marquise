"""Read port for cinema-source assignment display data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CinemaSourceAssignmentData:
    """Display data for one cinema-source assignment."""

    cinema_id: str
    source_display_name: str


class CinemaSourceAssignmentReader(ABC):
    """Read cinema-source assignments without constructing domain entities."""

    @abstractmethod
    async def list_all(self) -> list[CinemaSourceAssignmentData]:
        """Return every cinema-source assignment's display data."""
        ...
