"""Cinema-source assignment gateway protocol for persistence."""

from __future__ import annotations

from typing import Optional, Protocol


class CinemaSourceAssignmentGateway(Protocol):
    """Protocol for cinema_source_assignments table persistence.

    Implementations execute the actual SQL or API calls.  All methods return
    plain dicts or primitives — no domain entities.
    """

    async def assign(self, cinema_id: str, source_name: str) -> dict:
        """Upsert a cinema-source assignment.

        Args:
            cinema_id: The cinema identifier.
            source_name: The source name to assign.

        Returns:
            The inserted or updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        ...

    async def unassign(self, cinema_id: str) -> bool:
        """Remove the source assignment for a cinema.

        Args:
            cinema_id: The cinema to unassign.

        Returns:
            True if a row was deleted, False if none existed.
        """
        ...

    async def find_by_cinema_id(self, cinema_id: str) -> Optional[dict]:
        """Find the source name assigned to a cinema.

        Args:
            cinema_id: The cinema identifier.

        Returns:
            A dict with keys ``cinema_id`` and ``source_name``, or None.
        """
        ...

    async def find_all(self) -> list[dict]:
        """Retrieve all cinema-source assignments.

        Returns:
            A list of dicts with keys ``cinema_id`` and ``source_name``.
        """
        ...
