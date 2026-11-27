"""Cinema data gateway protocol."""

from __future__ import annotations

from typing import Protocol

from marquise.interface_adapters.gateways.base import (
    GatewayError,
    GatewayPage,
)

__all__ = ["CinemaGateway", "GatewayError", "GatewayPage"]


class CinemaGateway(Protocol):
    """Protocol for cinema data access.

    Implementations execute the actual SQL or API calls.  All methods return
    plain dicts or primitives — no domain entities, no ORM models.
    """

    async def save(
        self,
        cinema_id: str,
        name: str,
        address: str | None,
        city: str | None,
        website: str | None = None,
    ) -> dict:
        """Insert a cinema row.

        Args:
            cinema_id: Unique identifier for the cinema.
            name: Display name of the cinema.
            address: Street address (optional).
            city: City where the cinema is located (optional).
            website: Cinema website URL (optional).

        Returns:
            The inserted row as a dict.

        Raises:
            GatewayError: If a row with the given ``cinema_id`` already exists.
        """
        ...

    async def find_by_id(self, cinema_id: str) -> dict | None:
        """Find a cinema by its ID.

        Args:
            cinema_id: The unique identifier to look up.

        Returns:
            A dict representing the cinema row, or None if not found.
        """
        ...

    async def find_by_name_and_address(
        self, name: str, address: str | None
    ) -> dict | None:
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

    async def update(
        self,
        cinema_id: str,
        name: str,
        address: str | None,
        city: str | None,
        website: str | None = None,
    ) -> dict | None:
        """Update an existing cinema row.

        Args:
            cinema_id: The ID of the cinema to update.
            name: Updated display name.
            address: Updated street address (optional).
            city: Updated city (optional).
            website: Updated website URL (optional).

        Returns:
            The updated row as a dict, or None if no row with the given
            ``cinema_id`` exists.
        """
        ...

    async def delete(self, cinema_id: str) -> bool:
        """Delete a cinema by its ID.

        Args:
            cinema_id: The ID of the cinema to delete.

        Returns:
            True if a row was deleted, False otherwise.
        """
        ...

    async def find_all(
        self,
        name_filter: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
        """Retrieve cinemas, optionally filtered by name and paginated.

        Args:
            name_filter: An optional substring to match against cinema names
                (case-insensitive). If None, all cinemas are returned.
            limit: Max number of rows to return. If None, all matching rows
                are returned unbounded.
            offset: Number of matching rows to skip before returning results.

        Returns:
            A ``GatewayPage`` with the matching rows and the total count.
        """
        ...
