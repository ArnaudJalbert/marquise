"""Screening data gateway protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol


class ScreeningGateway(Protocol):
    """Protocol for screening data access.

    Implementations execute SQL or API calls and return plain dicts.
    """

    async def save(
        self,
        screening_id: str,
        movie_id: str,
        cinema_id: str,
        showtime: datetime,
        external_id: Optional[str] = None,
        ticket_url: Optional[str] = None,
        room: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """Insert a screening row (no-op on conflict).

        Uses a unique constraint on (cinema_id, movie_id, showtime).

        Args:
            screening_id: Unique identifier.
            movie_id: The movie being screened.
            cinema_id: The cinema hosting the screening.
            showtime: The date and time of the screening.
            external_id: Source-native deduplication key (optional).
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).

        Returns:
            The inserted or existing row as a dict.  The dict includes an
            ``__inserted`` key with a boolean value: ``True`` if a new row
            was created, ``False`` if an existing row was matched.

        Raises:
            GatewayError: On data-layer failure.
        """
        ...

    async def update(
        self,
        cinema_id: str,
        movie_id: str,
        showtime: datetime,
        external_id: Optional[str] = None,
        ticket_url: Optional[str] = None,
        room: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[dict]:
        """Update optional fields on an existing screening.

        Matches by (cinema_id, movie_id, showtime).

        Args:
            cinema_id: The cinema hosting the screening.
            movie_id: The movie being screened.
            showtime: The date and time of the screening.
            external_id: Source-native deduplication key (optional).
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).

        Returns:
            The updated row as a dict, or None if no matching row exists.
        """
        ...

    async def find_by_id(self, screening_id: str) -> Optional[dict]:
        """Find a screening by its ID.

        Args:
            screening_id: The unique identifier.

        Returns:
            A dict representing the row, or None.
        """
        ...

    async def find_by_cinema_and_date_range(
        self,
        cinema_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """Find screenings for a cinema within a date range.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).

        Returns:
            A list of dicts representing matching rows.
        """
        ...
