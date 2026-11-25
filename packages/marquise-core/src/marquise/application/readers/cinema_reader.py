"""Read port for cinema display data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class CinemaReader(ABC):
    """Read cinema display data without constructing domain entities."""

    @dataclass(frozen=True, slots=True)
    class CinemaData:
        """Display data for one cinema."""

        id: str
        name: str
        address: str | None = None
        city: str | None = None
        website: str | None = None

    @abstractmethod
    async def find_by_id(self, cinema_id: str) -> CinemaData | None:
        """Return one cinema projection, or None when its ID is missing."""
        ...
