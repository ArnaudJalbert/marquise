"""Abstract repository for screening persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from marquise.application.repositories.page import Page
from marquise.domain.entities import Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId


class ScreeningRepository(ABC):
    """Abstract interface for screening data persistence."""

    @abstractmethod
    async def save(self, screening: Screening) -> tuple[Screening, bool]:
        """Persist a new screening entity.

        Args:
            screening: The screening to save.

        Returns:
            A tuple of (saved_screening, was_inserted) where ``was_inserted``
            is True if a new row was created, False if an existing row was
            found.

        Raises:
            ScreeningAlreadyExistsError: If the screening's ``external_id``
                collides with a different existing screening.
        """
        ...

    @abstractmethod
    async def update(self, screening: Screening) -> Screening | None:
        """Update optional fields on an existing screening.

        Matches by (cinema_id, movie_id, showtime).  Fields set to None
        are left unchanged.

        Args:
            screening: The screening with updated optional fields.

        Returns:
            The updated screening entity, or None if no matching row exists.
        """
        ...

    @abstractmethod
    async def find_by_id(self, screening_id: ScreeningId) -> Screening | None:
        """Retrieve a screening by its unique identifier.

        Args:
            screening_id: The ID of the screening to find.

        Returns:
            The matching screening, or None if not found.
        """
        ...

    @abstractmethod
    async def search(
        self,
        movie_id: MovieId | None = None,
        movie_title: str | None = None,
        cinema_id: CinemaId | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        language: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[Screening]:
        """Find screenings matching any combination of filters, paginated.

        All filters are optional and combinable. Omitting a filter means it
        is not applied.

        Args:
            movie_id: Filter by exact movie ID.
            movie_title: Filter by movie title substring (case-insensitive).
            cinema_id: Filter by exact cinema ID.
            start_date: Start of the showtime range (inclusive).
            end_date: End of the showtime range (inclusive).
            language: Filter by exact language/subtitle version.
            limit: Max number of screenings to return. If None, all matching
                screenings are returned unbounded.
            offset: Number of matching screenings to skip before returning
                results.

        Returns:
            A ``Page[Screening]`` with the matching screenings and the total
            count matching the filters, ignoring ``limit``/``offset``.
        """
        ...

    @abstractmethod
    async def find_distinct_movies_by_cinema(
        self,
        cinema_id: CinemaId,
        start_date: datetime,
        end_date: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[Movie]:
        """Find distinct movies with a screening at a cinema in a date range.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the showtime range (inclusive).
            end_date: End of the showtime range (inclusive).
            limit: Max number of movies to return. If None, all matching
                movies are returned unbounded.
            offset: Number of matching movies to skip before returning
                results.

        Returns:
            A ``Page[Movie]`` with the matching movies and the total count of
            distinct movies matching the cinema and date range, ignoring
            ``limit``/``offset``.
        """
        ...
