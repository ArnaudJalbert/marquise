"""Abstract repository for movie persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

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
    async def find_by_title(self, title: str) -> Movie | None:
        """Find a movie by its exact title.

        Args:
            title: The movie title to search for.

        Returns:
            The matching movie, or None if not found.
        """
        ...
