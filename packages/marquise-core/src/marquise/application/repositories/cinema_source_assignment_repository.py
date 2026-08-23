"""Abstract repository for cinema-source assignment persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from marquise.domain.entities import CinemaSourceAssignment
from marquise.domain.value_objects import CinemaId


class CinemaSourceAssignmentRepository(ABC):
    """Abstract interface for cinema-source assignment data persistence."""

    @abstractmethod
    async def assign(
        self, assignment: CinemaSourceAssignment
    ) -> CinemaSourceAssignment:
        """Persist a cinema-source assignment.

        Args:
            assignment: The assignment to save.

        Returns:
            The saved assignment.
        """
        ...

    @abstractmethod
    async def unassign(self, cinema_id: CinemaId) -> bool:
        """Remove the source assignment for a cinema.

        Args:
            cinema_id: The cinema to unassign.

        Returns:
            True if an assignment was removed, False if none existed.
        """
        ...

    @abstractmethod
    async def find_by_cinema_id(
        self, cinema_id: CinemaId
    ) -> CinemaSourceAssignment | None:
        """Find the source assignment for a given cinema.

        Args:
            cinema_id: The cinema to look up.

        Returns:
            The matching assignment, or None if not found.
        """
        ...
