"""Abstract repository for cinema persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


class CinemaRepository(ABC):
    """Abstract interface for cinema data persistence.

    Defines the contract that any concrete cinema repository must fulfil.
    """

    @abstractmethod
    async def save(self, cinema: Cinema) -> Cinema:
        """Persist a cinema entity.

        Args:
            cinema: The cinema to save (may include an unsaved ID).

        Returns:
            The saved cinema with its assigned ID.
        """
        ...

    @abstractmethod
    async def find_by_id(self, cinema_id: CinemaId) -> Cinema | None:
        """Retrieve a cinema by its unique identifier.

        Args:
            cinema_id: The ID of the cinema to find.

        Returns:
            The matching cinema, or None if not found.
        """
        ...

    @abstractmethod
    async def find_by_name_and_address(
        self, name: str, address: str | None
    ) -> Cinema | None:
        """Find a cinema by its exact name and address.

        Args:
            name: The cinema name.
            address: The cinema address (may be None).

        Returns:
            The matching cinema, or None if not found.
        """
        ...

    @abstractmethod
    async def exists_by_id(self, cinema_id: CinemaId) -> bool:
        """Check whether a cinema exists with the given ID.

        Args:
            cinema_id: The ID to check for.

        Returns:
            True if a cinema with that ID exists, False otherwise.
        """
        ...

    @abstractmethod
    async def find_all(self, name_filter: str | None = None) -> list[Cinema]:
        """Retrieve all cinemas, optionally filtered by name.

        Args:
            name_filter: An optional substring to match against cinema names
                (case-insensitive). If None, all cinemas are returned.

        Returns:
            A list of cinema entities matching the filter.
        """
        ...

    @abstractmethod
    async def update(self, cinema: Cinema) -> Cinema:
        """Update an existing cinema.

        Args:
            cinema: The cinema entity with updated fields. The ID must match
                an existing cinema.

        Returns:
            The updated cinema as returned by the data store.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        ...

    @abstractmethod
    async def delete(self, cinema_id: CinemaId) -> bool:
        """Delete a cinema by its unique identifier.

        Args:
            cinema_id: The ID of the cinema to delete.

        Returns:
            True if a cinema was deleted, False if no cinema with that ID
            was found.
        """
        ...
