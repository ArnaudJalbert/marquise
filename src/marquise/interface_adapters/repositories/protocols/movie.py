"""Movie data gateway protocol."""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol


class MovieGateway(Protocol):
    """Protocol for movie data access.

    Implementations execute SQL or API calls and return plain dicts.
    """

    async def save(
        self,
        movie_id: str,
        title: str,
        release_date: Optional[date],
        directors: Optional[str] = None,
        cast: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        description: Optional[str] = None,
    ) -> dict:
        """Insert or upsert a movie row.

        Uses a unique constraint on title.

        Args:
            movie_id: Unique identifier.
            title: Movie title.
            release_date: Release date (optional when unknown).
            directors: Comma-separated directors (None if unknown).
            cast: Comma-separated cast (None if unknown).
            duration_minutes: Duration in minutes.
            description: Movie description.

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        ...

    async def find_by_id(self, movie_id: str) -> Optional[dict]:
        """Find a movie by its ID.

        Args:
            movie_id: The unique identifier.

        Returns:
            A dict representing the row, or None.
        """
        ...

    async def find_by_title(self, title: str) -> Optional[dict]:
        """Find a movie by its exact title.

        Args:
            title: The movie title.

        Returns:
            A dict representing the row, or None.
        """
        ...
