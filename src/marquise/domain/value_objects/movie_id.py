"""Movie ID value object."""

from __future__ import annotations

from dataclasses import dataclass

from .id_value import IdValue


@dataclass(frozen=True, slots=True)
class MovieId(IdValue):
    """Unique identifier for a movie."""
