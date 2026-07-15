"""Source definition entity representing a registered showtime source."""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects import SourceName


@dataclass(kw_only=True, slots=True)
class SourceDefinition:
    """A registered showtime source in the Marquise catalog.

    Attributes:
        name: Unique machine name (e.g. ``'cineplex'``).
        display_name: Human-readable label (e.g. ``'Cineplex'``).
        description: Optional longer description.
    """

    name: SourceName
    display_name: str
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate source definition data.

        Raises:
            ValueError: If ``name`` or ``display_name`` is empty.
        """
        if not self.display_name.strip():
            raise ValueError("Source display_name cannot be empty")
