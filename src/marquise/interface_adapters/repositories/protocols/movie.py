"""Movie data gateway protocol."""

from __future__ import annotations

from typing import Protocol

from marquise.interface_adapters.repositories.protocols.base import GatewayPage

__all__ = ["GatewayPage", "MovieGateway"]


class MovieGateway(Protocol):
    """Protocol for movie data access.

    Implementations execute SQL or API calls and return plain dicts.
    """

    async def save(
        self,
        movie_id: str,
        title: str,
        release_year: int | None = None,
        directors: str | None = None,
        cast: str | None = None,
        duration_minutes: int | None = None,
        description: str | None = None,
        poster_url: str | None = None,
        trailer_url: str | None = None,
        genres: str | None = None,
        original_title: str | None = None,
        rating: str | None = None,
        origin_countries: str | None = None,
    ) -> dict:
        """Insert or upsert a movie row.

        Uses a unique constraint on title.

        Args:
            movie_id: Unique identifier.
            title: Movie title.
            release_year: Release year (optional when unknown).
            directors: Comma-separated directors (None if unknown).
            cast: Comma-separated cast (None if unknown).
            duration_minutes: Duration in minutes.
            description: Movie description.
            poster_url: URL to movie poster image (optional).
            trailer_url: URL to movie trailer (optional).
            genres: Comma-separated genres (optional).
            original_title: Original title in native language (optional).
            rating: Content rating (optional).
            origin_countries: Comma-separated origin countries (optional).

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        ...

    async def find_by_id(self, movie_id: str) -> dict | None:
        """Find a movie by its ID.

        Args:
            movie_id: The unique identifier.

        Returns:
            A dict representing the row, or None.
        """
        ...

    async def find_by_title(self, title: str) -> dict | None:
        """Find a movie by title, case-insensitively.

        Args:
            title: The movie title.

        Returns:
            A dict representing the row, or None.
        """
        ...

    async def find_all(
        self,
        title_filter: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
        """Retrieve movies, optionally filtered by title and paginated.

        Args:
            title_filter: An optional substring to match against movie
                titles (case-insensitive). If None, all movies are returned.
            limit: Max number of rows to return. If None, all matching rows
                are returned unbounded.
            offset: Number of matching rows to skip before returning results.

        Returns:
            A ``GatewayPage`` with the matching rows and the total count.
        """
        ...
