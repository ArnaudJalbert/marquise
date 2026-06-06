"""Cinema entity representing a movie theater."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..value_objects import CinemaId


@dataclass(kw_only=True, slots=True)
class Cinema:
    """Represents a cinema or movie theater."""

    id: CinemaId
    name: str
    address: Optional[str] = None
    city: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate cinema data."""
        if not self.name.strip():
            raise ValueError("Cinema name cannot be empty")

    def is_located_in(self, city: str) -> bool:
        """Check if the cinema is located in a specific city."""
        return self.city is not None and self.city.lower() == city.lower()
