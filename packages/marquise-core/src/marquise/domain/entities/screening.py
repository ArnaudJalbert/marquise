"""Screening entity - represents a specific movie screening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

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
        source_name: Source that owns the external identifier (optional).
        ticket_url: Link to purchase tickets (optional).
        room: Room or auditorium name (optional).
        language: Language or subtitle version (optional).
    """

    id: ScreeningId
    movie: Movie
    cinema: Cinema
    showtime: Showtime
    external_id: str | None = None
    source_name: str | None = None
    ticket_url: str | None = None
    room: str | None = None
    language: str | None = None

    def can_reschedule_to(self, incoming: Screening) -> bool:
        """Check verified native ownership and the Montreal calendar date."""
        zone = ZoneInfo("America/Montreal")
        return bool(
            self.cinema.id == incoming.cinema.id
            and self.movie.id == incoming.movie.id
            and self.external_id
            and self.external_id == incoming.external_id
            and self.source_name
            and self.source_name == incoming.source_name
            and self.showtime.value.astimezone(zone).date()
            == incoming.showtime.value.astimezone(zone).date()
        )

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
