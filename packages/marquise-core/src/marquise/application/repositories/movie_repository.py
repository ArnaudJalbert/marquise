"""Abstract repository for movie persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from marquise.application.repositories.page import Page
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


class MovieRepository(ABC):
    """Abstract interface for movie data persistence."""

    @abstractmethod
    async def save(self, movie: Movie) -> Movie:
        """Persists a movie entity.

        Args:
            movie: The movie to save.

        Returns:
            The saved movie with its assigned ID.
        """
        ...

    @abstractmethod
    async def find_by_id(self, movie_id: MovieId) -> Movie | None:
        """Retrieve a movie by its unique identifier.

        Args:
            movie_id: The ID of the movie to find.

        Returns:
            The matching movie, or None if not found.
        """
        ...

    @abstractmethod
    async def find_by_ids(self, movie_ids: list[MovieId]) -> list[Movie]:
        """Retrieve movies by a list of unique identifiers.

        Args:
            movie_ids: The IDs of the movies to find.

        Returns:
            The matching movies. IDs with no matching movie are silently
            omitted — the returned list may be shorter than ``movie_ids``.
        """
        ...

    @abstractmethod
    async def find_by_tmdb_id(self, tmdb_id: str) -> Movie | None:
        """Find a movie by its TMDB film id, or return None."""
        ...

    @abstractmethod
    async def find_by_title(self, title: str) -> Movie | None:
        """Find a movie by title, case-insensitively.

        Args:
            title: The movie title to search for.

        Returns:
            The matching movie, or None if not found.
        """
        ...

    @abstractmethod
    async def find_by_titles(self, titles: list[str]) -> list[Movie]:
        """Find candidate movies containing any title term, case-insensitively.

        Args:
            titles: The title terms to search for.

        Returns:
            Candidate Movie entities. Terms with no match are silently omitted.
        """
        ...

    @abstractmethod
    async def exists_by_id(self, movie_id: MovieId) -> bool:
        """Check whether a movie exists with the given ID.

        Args:
            movie_id: The ID to check for.

        Returns:
            True if a movie with that ID exists, False otherwise.
        """
        ...

    @abstractmethod
    async def find_all(
        self,
        title_filter: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[Movie]:
        """Retrieve movies, optionally filtered by title and paginated.

        Args:
            title_filter: An optional substring to match against movie
                titles (case-insensitive). If None, all movies are returned.
            limit: Max number of movies to return. If None, all matching
                movies are returned unbounded.
            offset: Number of matching movies to skip before returning
                results.

        Returns:
            A ``Page[Movie]`` with the matching movies and the total count
            matching ``title_filter``, ignoring ``limit``/``offset``.
        """
        ...
