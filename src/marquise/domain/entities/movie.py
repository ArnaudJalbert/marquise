"""Movie entity representing a film."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from ..value_objects import MovieId


@dataclass(kw_only=True, slots=True)
class Movie:
    """A movie with its core details.

    Attributes:
        id: Unique identifier for the movie.
        title: Official title of the movie.
        release_year: Theatrical release year (None if unknown).
        directors: Tuple of director names (None if unknown).
        cast: Tuple of cast member names (None if unknown).
        duration_minutes: Runtime in minutes (optional).
        description: Plot synopsis (optional).
        poster_url: URL to the movie poster image (optional).
        trailer_url: URL to the movie trailer (optional).
        genres: Tuple of genre names (optional).
        original_title: Original title in native language (optional).
        rating: Content rating (e.g. ``"18+"``) (optional).
        origin_countries: Tuple of production country names (optional).
    """

    id: MovieId
    title: str
    release_year: Optional[int] = None
    directors: Optional[Tuple[str, ...]] = None
    cast: Optional[Tuple[str, ...]] = None
    duration_minutes: Optional[int] = None
    description: Optional[str] = None
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    genres: Optional[Tuple[str, ...]] = None
    original_title: Optional[str] = None
    rating: Optional[str] = None
    origin_countries: Optional[Tuple[str, ...]] = None

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
        if self.release_year is not None and self.release_year <= 0:
            raise ValueError("Movie release year must be positive")

    def is_recent(self, years: int = 1) -> bool:
        """Check if the movie was released within the last specified years.

        Args:
            years: Number of years to consider as "recent" (default 1).

        Returns:
            True if the movie's release year is within the given window,
            False if the release year is unknown.
        """
        if self.release_year is None:
            return False
        return datetime.now().year - self.release_year <= years
