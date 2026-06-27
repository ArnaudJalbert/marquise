"""Abstract repository for screening persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from marquise.domain.entities import Screening
from marquise.domain.value_objects import CinemaId, ScreeningId


class ScreeningRepository(ABC):
    """Abstract interface for screening data persistence."""

    @abstractmethod
    async def save(self, screening: Screening) -> tuple[Screening, bool]:
        """Persist a new screening entity.

        Args:
            screening: The screening to save.

        Returns:
            A tuple of (saved_screening, was_inserted) where ``was_inserted``
            is True if a new row was created, False if an existing row was
            found.
        """
        ...

    @abstractmethod
    async def update(self, screening: Screening) -> Screening | None:
        """Update optional fields on an existing screening.

        Matches by (cinema_id, movie_id, showtime).  Fields set to None
        are left unchanged.

        Args:
            screening: The screening with updated optional fields.

        Returns:
            The updated screening entity, or None if no matching row exists.
        """
        ...

    @abstractmethod
    async def find_by_id(self, screening_id: ScreeningId) -> Screening | None:
        """Retrieve a screening by its unique identifier.

        Args:
            screening_id: The ID of the screening to find.

        Returns:
            The matching screening, or None if not found.
        """
        ...

    @abstractmethod
    async def find_by_cinema_and_date_range(
        self,
        cinema_id: CinemaId,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Screening]:
        """Find all screenings for a cinema within a date range.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).

        Returns:
            A list of matching screening entities.
        """
        ...
