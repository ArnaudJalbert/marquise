"""Showtime value object."""

from __future__ import annotations

from dataclasses import dataclass

from .date_value import DateValue


@dataclass(frozen=True, slots=True)
class Showtime(DateValue):
    """Time of a screening."""
