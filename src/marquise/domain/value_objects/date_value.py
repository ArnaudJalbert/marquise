"""Showtime value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DateValue:
    """Date for a value object"""

    value: datetime

    @classmethod
    def from_datetime(cls, dt: datetime) -> DateValue:
        """Create a Showtime from a datetime."""
        return cls(value=dt)

    def __str__(self) -> str:
        return self.value.isoformat()

    def __hash__(self) -> int:
        return hash(self.value)
