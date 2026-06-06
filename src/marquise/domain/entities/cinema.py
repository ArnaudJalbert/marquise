"""Cinema entity representing a movie theater."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..value_objects import CinemaId


@dataclass(kw_only=True, slots=True)
class Cinema:
    """A physical cinema or movie theater location.

    Attributes:
        id: Unique identifier for the cinema.
        name: Display name of the cinema.
        address: Street address (optional).
        city: City where the cinema is located (optional).
    """

    id: CinemaId
    name: str
    address: Optional[str] = None
    city: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate cinema data after initialization.

        Raises:
            ValueError: If the cinema name is empty or whitespace-only.
        """
        if not self.name.strip():
            raise ValueError("Cinema name cannot be empty")

    def is_located_in(self, city: str) -> bool:
        """Check if the cinema is located in a specific city.

        Args:
            city: The city name to check against (case-insensitive).

        Returns:
            True if the cinema's city matches the given city, False otherwise.
        """
        return self.city is not None and self.city.lower() == city.lower()
