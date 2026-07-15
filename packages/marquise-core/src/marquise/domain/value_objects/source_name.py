"""Source name value object."""

from __future__ import annotations

from dataclasses import dataclass

from .id_value import IdValue


@dataclass(frozen=True, slots=True)
class SourceName(IdValue):
    """Unique machine name identifying a showtime source (e.g. 'cineplex')."""
