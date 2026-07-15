"""Date value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DateValue:
    """An immutable datetime wrapper for value objects.

    Attributes:
        value: The underlying datetime value (must be timezone-aware).
    """

    value: datetime

    def __post_init__(self) -> None:
        """Validate that value is timezone-aware.

        Raises:
            ValueError: If value is a naive datetime (no tzinfo).
        """
        if self.value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")

    @classmethod
    def from_datetime(cls, dt: datetime) -> DateValue:
        """Create a DateValue from a datetime instance.

        Args:
            dt: The datetime to wrap (must be timezone-aware).

        Returns:
            A new DateValue instance.
        """
        return cls(value=dt)

    def __str__(self) -> str:
        return self.value.isoformat()
