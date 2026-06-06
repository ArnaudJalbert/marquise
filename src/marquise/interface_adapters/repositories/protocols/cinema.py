"""Cinema data gateway protocol."""

from __future__ import annotations

from typing import Optional, Protocol


class GatewayError(Exception):
    """Raised when a gateway operation fails at the data layer."""


class CinemaGateway(Protocol):
    """Protocol for cinema data access.

    Implementations execute the actual SQL or API calls.  All methods return
    plain dicts or primitives — no domain entities, no ORM models.
    """

    async def save(
        self, cinema_id: str, name: str, address: Optional[str], city: Optional[str]
    ) -> dict:
        """Insert a cinema row.

        Args:
            cinema_id: Unique identifier for the cinema.
            name: Display name of the cinema.
            address: Street address (optional).
            city: City where the cinema is located (optional).

        Returns:
            The inserted row as a dict.

        Raises:
            GatewayError: If a row with the given ``cinema_id`` already exists.
        """
        ...

    async def find_by_id(self, cinema_id: str) -> Optional[dict]:
        """Find a cinema by its ID.

        Args:
            cinema_id: The unique identifier to look up.

        Returns:
            A dict representing the cinema row, or None if not found.
        """
        ...

    async def find_by_name_and_address(
        self, name: str, address: Optional[str]
    ) -> Optional[dict]:
        """Find a cinema by its exact name and address.

        Args:
            name: The cinema name.
            address: The cinema address (may be None).

        Returns:
            A dict representing the cinema row, or None if not found.
        """
        ...

    async def exists_by_id(self, cinema_id: str) -> bool:
        """Check whether a cinema exists with the given ID.

        Args:
            cinema_id: The ID to check for.

        Returns:
            True if a row with that ID exists, False otherwise.
        """
        ...
