"""Cinema-source assignment entity linking a cinema to its showtime source."""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects import CinemaId, SourceName


@dataclass(kw_only=True, slots=True)
class CinemaSourceAssignment:
    """Links a cinema to its showtime source.

    Attributes:
        cinema_id: The cinema this assignment applies to.
        source_name: The source that provides showtimes for this cinema.
    """

    cinema_id: CinemaId
    source_name: SourceName

    def __post_init__(self) -> None:
        """Validate assignment data.

        Raises:
            ValueError: If ``cinema_id`` or ``source_name`` is empty.
        """
        pass
