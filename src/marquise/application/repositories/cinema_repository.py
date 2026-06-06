"""Abstract repository for cinema persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


class CinemaRepository(ABC):
    """Abstract repository for cinema data persistence."""

    @abstractmethod
    async def save(self, cinema: Cinema) -> Cinema:
        """Save a cinema. Returns saved cinema with ID."""
        ...

    @abstractmethod
    async def find_by_id(self, cinema_id: CinemaId) -> Optional[Cinema]:
        """Find a cinema by its ID."""
        ...

    @abstractmethod
    async def find_by_name_and_address(
        self, name: str, address: Optional[str]
    ) -> Optional[Cinema]:
        """Find a cinema by its name and address."""
        ...

    @abstractmethod
    async def exists_by_id(self, cinema_id: CinemaId) -> bool:
        """Check if a cinema exists with the given ID."""
        ...
