"""Abstract repository for cinema persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

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
    async def find_by_id(self, cinema_id: CinemaId) -> Optional[Cinema]:
        """Retrieve a cinema by its unique identifier.

        Args:
            cinema_id: The ID of the cinema to find.

        Returns:
            The matching cinema, or None if not found.
        """
        ...

    @abstractmethod
    async def find_by_name_and_address(
        self, name: str, address: Optional[str]
    ) -> Optional[Cinema]:
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
