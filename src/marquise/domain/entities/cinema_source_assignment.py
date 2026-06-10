"""Cinema-source assignment entity linking a cinema to its showtime source."""

from __future__ import annotations

from dataclasses import dataclass

from .cinema import Cinema
from .source_definition import SourceDefinition


@dataclass(kw_only=True, slots=True)
class CinemaSourceAssignment:
    """Links a cinema to its showtime source.

    Attributes:
        cinema: The cinema this assignment applies to.
        source: The source that provides showtimes for this cinema.
    """

    cinema: Cinema
    source: SourceDefinition
