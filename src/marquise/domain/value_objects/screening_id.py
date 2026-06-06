"""Screening ID value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreeningId:
    """Unique identifier for a screening.

    Attributes:
        value: The unique string identifier for the screening.
    """

    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)
