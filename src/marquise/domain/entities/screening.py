"""Screening entity - represents a specific movie screening."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..exceptions import ScreeningError
from ..value_objects import CinemaId, MovieId, Price, ScreeningId, Showtime


@dataclass(kw_only=True, slots=True)
class Screening:
    """A screening of a movie at a cinema at a specific time.

    Attributes:
        id: Unique identifier for the screening.
        movie_id: Identifier of the movie being screened.
        cinema_id: Identifier of the cinema hosting the screening.
        showtime: Date and time of the screening.
        price: Ticket price.
        available_seats: Number of seats still available (set externally).
        is_sold_out: Whether the screening is sold out (set externally).
    """

    id: ScreeningId
    movie_id: MovieId
    cinema_id: CinemaId
    showtime: Showtime
    price: Price
    available_seats: Optional[int] = field(default=None, init=False)
    is_sold_out: Optional[bool] = field(default=None, init=False)

    def is_upcoming(self, now: Optional[datetime] = None) -> bool:
        """Check if this screening is still in the future.

        Args:
            now: Reference time (defaults to current UTC time).

        Returns:
            True if the showtime is after the reference time.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        return self.showtime.value > now

    def has_ended(self, now: Optional[datetime] = None) -> bool:
        """Check if this screening has already ended.

        Args:
            now: Reference time (defaults to current UTC time).

        Returns:
            True if the showtime is before the reference time.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        return self.showtime.value < now

    def update_availability(self, seats_sold: int) -> None:
        """Reduce available seats after selling tickets.

        Args:
            seats_sold: Number of tickets sold.

        Raises:
            ScreeningError: If seats are unknown, seats_sold is negative,
                or more seats are sold than available.
        """
        if self.available_seats is None:
            raise ScreeningError("Cannot update availability: seats unknown")
        if seats_sold < 0:
            raise ScreeningError("Seats sold cannot be negative")
        if seats_sold > self.available_seats:
            raise ScreeningError("Cannot sell more seats than available")
        self.available_seats -= seats_sold
        self.is_sold_out = self.available_seats == 0

    def __str__(self) -> str:
        return (
            f"Screening(movie={self.movie_id},"
            f" cinema={self.cinema_id},"
            f" showtime={self.showtime})"
        )
