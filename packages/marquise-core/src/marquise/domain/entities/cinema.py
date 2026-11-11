"""Cinema entity representing a movie theater."""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects import CinemaId


@dataclass(kw_only=True, slots=True)
class Cinema:
    """A physical cinema or movie theater location.

    Attributes:
        id: Unique identifier for the cinema.
        name: Display name of the cinema.
        address: Street address (optional).
        city: City where the cinema is located (optional).
        website: Cinema's website URL (optional).
    """

    id: CinemaId
    name: str
    address: str | None = None
    city: str | None = None
    website: str | None = None

    def __post_init__(self) -> None:
        """Validate cinema data after initialization.

        Raises:
            ValueError: If the cinema name is empty or whitespace-only.
        """
        if not self.name.strip():
            raise ValueError("Cinema name cannot be empty")
