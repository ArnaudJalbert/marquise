"""Date value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DateValue:
    """An immutable datetime wrapper for value objects.

    Attributes:
        value: The underlying datetime value.
    """

    value: datetime

    @classmethod
    def from_datetime(cls, dt: datetime) -> DateValue:
        """Create a DateValue from a datetime instance.

        Args:
            dt: The datetime to wrap.

        Returns:
            A new DateValue instance.
        """
        return cls(value=dt)

    def __str__(self) -> str:
        return self.value.isoformat()

    def __hash__(self) -> int:
        return hash(self.value)
