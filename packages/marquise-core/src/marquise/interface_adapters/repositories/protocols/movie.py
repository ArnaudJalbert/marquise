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
        tmdb_id: str | None = None,
        tmdb_rating: float | None = None,
        tmdb_vote_count: int | None = None,
        *,
        update_existing: bool = True,
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
            tmdb_id: Known TMDB identity, if any.
            tmdb_rating: TMDB user score, if fetched.
            tmdb_vote_count: TMDB vote count, if fetched.
            update_existing: Update matching titles, or return them unchanged.

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        ...

    async def find_by_tmdb_id(self, tmdb_id: str) -> dict | None:
        """Find a movie by its TMDB film id, or return None."""
        ...

    async def find_by_id(self, movie_id: str) -> dict | None:
        """Find a movie by its ID.

        Args:
            movie_id: The unique identifier.

        Returns:
            A dict representing the row, or None.
        """
        ...

    async def find_by_ids(self, movie_ids: list[str]) -> list[dict]:
        """Find movies by a list of IDs.

        Args:
            movie_ids: The unique identifiers to look up.

        Returns:
            A dict per matching row. IDs with no matching row are silently
            omitted.
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

    async def find_by_titles(self, titles: list[str]) -> list[dict]:
        """Find candidate movies containing any title term, case-insensitively.

        Args:
            titles: The title terms to search for.

        Returns:
            A dict per matching row. Terms with no match are silently omitted.
        """
        ...

    async def exists_by_id(self, movie_id: str) -> bool:
        """Check whether a movie exists with the given ID.

        Args:
            movie_id: The ID to check for.

        Returns:
            True if a row with that ID exists, False otherwise.
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
