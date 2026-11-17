"""Hour filter value objects for Montréal screening times."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HourRange:
    """One half-open whole-hour Montréal range."""

    start: int
    end: int

    def __post_init__(self) -> None:
        """Reject empty, inverted, or out-of-day ranges."""
        if not 0 <= self.start < self.end <= 24:
            raise ValueError("hours must satisfy 0 <= start < end <= 24")


@dataclass(frozen=True, slots=True)
class HourFilter:
    """Hour ranges matched together before optional exclusion."""

    ranges: tuple[HourRange, ...]
    excluded: bool = False

    def __post_init__(self) -> None:
        """Require at least one range."""
        if not self.ranges:
            raise ValueError("hours must include at least one range")
