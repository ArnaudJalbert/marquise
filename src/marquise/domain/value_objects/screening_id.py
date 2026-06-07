"""Screening ID value object."""

from __future__ import annotations

from dataclasses import dataclass

from .id_value import IdValue


@dataclass(frozen=True, slots=True)
class ScreeningId(IdValue):
    """Unique identifier for a screening.

    Attributes:
        value: The unique string identifier for the screening.
    """
