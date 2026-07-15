"""Cinema ID value object."""

from __future__ import annotations

from dataclasses import dataclass

from .id_value import IdValue


@dataclass(frozen=True, slots=True)
class CinemaId(IdValue):
    """Unique identifier for a cinema.

    Wraps a string value that uniquely identifies a cinema entity.
    """
