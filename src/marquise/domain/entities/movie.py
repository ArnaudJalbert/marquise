"""Movie entity representing a film."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple

from ..value_objects import MovieId


@dataclass(kw_only=True, slots=True)
class Movie:
    """A movie with its core details.

    Attributes:
        id: Unique identifier for the movie.
        title: Official title of the movie.
        release_date: Theatrical release date (None if unknown).
        directors: Tuple of director names (None if unknown).
        cast: Tuple of cast member names (None if unknown).
        duration_minutes: Runtime in minutes (optional).
        description: Plot synopsis (optional).
    """

    id: MovieId
    title: str
    release_date: Optional[date] = None
    directors: Optional[Tuple[str, ...]] = None
    cast: Optional[Tuple[str, ...]] = None
    duration_minutes: Optional[int] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate movie data after initialization.

        Raises:
            ValueError: If the title is empty, no directors are provided,
                a director name is empty, or duration is non-positive.
        """
        if not self.title.strip():
            raise ValueError("Movie title cannot be empty")
        if self.directors is not None:
            if not self.directors:
                raise ValueError("Movie must have at least one director")
            if not all(d.strip() for d in self.directors):
                raise ValueError("Director name cannot be empty")
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValueError("Movie duration must be positive")

    def is_recent(self, years: int = 1) -> bool:
        """Check if the movie was released within the last specified years.

        Args:
            years: Number of years to consider as "recent" (default 1).

        Returns:
            True if the movie's release date is within the given window,
            False if the release date is unknown.
        """
        if self.release_date is None:
            return False
        from datetime import datetime, timedelta

        cutoff_date = datetime.now().date() - timedelta(days=years * 365)
        return self.release_date > cutoff_date
