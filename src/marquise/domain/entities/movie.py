"""Movie entity representing a film."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple

from ..value_objects import MovieId


@dataclass(kw_only=True, slots=True)
class Movie:
    """Represents a movie with its core details."""

    id: MovieId
    title: str
    release_date: date
    directors: Tuple[str, ...]
    cast: Tuple[str, ...]
    duration_minutes: Optional[int] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate movie data."""
        if not self.title.strip():
            raise ValueError("Movie title cannot be empty")
        if not self.directors:
            raise ValueError("Movie must have at least one director")
        if not all(d.strip() for d in self.directors):
            raise ValueError("Director name cannot be empty")
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValueError("Movie duration must be positive")

    def is_recent(self, years: int = 1) -> bool:
        """Check if the movie was released within the last specified years."""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now().date() - timedelta(days=years * 365)
        return self.release_date > cutoff_date
