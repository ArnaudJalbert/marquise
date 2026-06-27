"""Screening entity - represents a specific movie screening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..value_objects import ScreeningId, Showtime
from .cinema import Cinema
from .movie import Movie


@dataclass(kw_only=True, slots=True)
class Screening:
    """A screening of a movie at a cinema at a specific time.

    Attributes:
        id: Unique identifier for the screening.
        movie: The movie being screened.
        cinema: The cinema hosting the screening.
        showtime: Date and time of the screening.
        external_id: Source-native identifier for deduplication (optional).
        ticket_url: Link to purchase tickets (optional).
        room: Room or auditorium name (optional).
        language: Language or subtitle version (optional).
    """

    id: ScreeningId
    movie: Movie
    cinema: Cinema
    showtime: Showtime
    external_id: str | None = None
    ticket_url: str | None = None
    room: str | None = None
    language: str | None = None

    def is_upcoming(self, now: datetime | None = None) -> bool:
        """Check if this screening is still in the future.

        Args:
            now: Reference time (defaults to current UTC time).

        Returns:
            True if the showtime is after the reference time.
        """
        if now is None:
            now = datetime.now(UTC)
        return self.showtime.value > now

    def has_ended(self, now: datetime | None = None) -> bool:
        """Check if this screening has already ended.

        Args:
            now: Reference time (defaults to current UTC time).

        Returns:
            True if the showtime is before the reference time.
        """
        if now is None:
            now = datetime.now(UTC)
        return self.showtime.value < now

    def __str__(self) -> str:
        return (
            f"Screening(movie={self.movie.id},"
            f" cinema={self.cinema.id},"
            f" showtime={self.showtime})"
        )
