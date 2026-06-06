"""Release date value object."""

from __future__ import annotations

from dataclasses import dataclass

from .date_value import DateValue


@dataclass(frozen=True, slots=True)
class ReleaseDate(DateValue):
    """Release date of a movie."""
