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
    ) -> dict:
        """Insert or upsert a screening row.

        Uses a unique constraint on (cinema_id, movie_id, showtime).

        Args:
            screening_id: Unique identifier.
            movie_id: The movie being screened.
            cinema_id: The cinema hosting the screening.
            showtime: The date and time of the screening.

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
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
