"""Screening entity - represents a specific movie screening."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..value_objects import ScreeningId, Showtime, Price
from ..exceptions import ScreeningError
from .movie import Movie
from .cinema import Cinema


@dataclass(kw_only=True, slots=True)
class Screening:
    """A screening of a movie at a cinema at a specific time."""

    id: ScreeningId
    movie_id: Movie
    cinema_id: Cinema
    showtime: Showtime
    price: Price
    available_seats: Optional[int] = field(default=None, init=False)
    is_sold_out: Optional[bool] = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Validate the screening data."""
        if self.available_seats is not None:
            if self.available_seats < 0:
                raise ScreeningError("Available seats cannot be negative")
        if self.price.value < 0:
            raise ScreeningError("Price cannot be negative")

    def is_upcoming(self, now: Optional[datetime] = None) -> bool:
        """Check if this screening is upcoming."""
        if now is None:
            now = datetime.utcnow()
        return self.showtime.value > now

    def has_ended(self, now: Optional[datetime] = None) -> bool:
        """Check if this screening has ended."""
        if now is None:
            now = datetime.utcnow()
        return self.showtime.value < now

    def update_availability(self, seats_sold: int) -> None:
        """Update available seats after selling tickets."""
        if self.available_seats is None:
            raise ScreeningError("Cannot update availability: seats unknown")
        if seats_sold < 0:
            raise ScreeningError("Seats sold cannot be negative")
        if seats_sold > self.available_seats:
            raise ScreeningError("Cannot sell more seats than available")
        self.available_seats -= seats_sold
        self.is_sold_out = self.available_seats == 0

    def __str__(self) -> str:
        return f"{self.movie_id} at {self.cinema_id} on {self.showtime}"
