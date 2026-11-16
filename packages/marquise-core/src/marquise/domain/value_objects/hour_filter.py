"""Hour filter value objects for Montréal screening times."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HourRange:
    """One half-open whole-hour Montréal range."""

    start: int
    end: int

    def __post_init__(self) -> None:
        """Check field types, then reject empty, inverted, or out-of-day ranges."""
        if not isinstance(self.start, int) or not isinstance(self.end, int):
            raise TypeError("start and end must be int")
        if not 0 <= self.start < self.end <= 24:
            raise ValueError("hours must satisfy 0 <= start < end <= 24")


@dataclass(frozen=True, slots=True)
class HourFilter:
    """Hour ranges matched together before optional exclusion."""

    ranges: tuple[HourRange, ...]
    excluded: bool = False

    def __post_init__(self) -> None:
        """Check field types, then require at least one range."""
        if not isinstance(self.ranges, tuple):
            raise TypeError("ranges must be a tuple")
        if not isinstance(self.excluded, bool):
            raise TypeError("excluded must be a bool")
        if not self.ranges:
            raise ValueError("hours must include at least one range")
