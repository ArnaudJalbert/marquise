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
    async def save(self, screening: Screening) -> Screening:
        """Persist a screening entity.

        Args:
            screening: The screening to save.

        Returns:
            The saved screening entity.

        Raises:
            ScreeningAlreadyExistsError: If a screening with the same
                (cinema_id, movie_id, showtime) already exists.
            ScreeningExternalIdConflictError: If the external ID belongs
                to a different screening.
        """
        ...

    @abstractmethod
    async def read_import_candidates(
        self, incoming: Screening
    ) -> tuple[Screening, ...]:
        """Return detached rows matching the Cinema/native key or target identity.

        Return every match, including ambiguous native ownership. An absent or
        empty native key matches only the target (Cinema, Movie, Showtime).
        This read makes no eligibility decision.
        """
        ...

    @abstractmethod
    async def commit_import(
        self,
        proposed: Screening,
        *,
        incoming: Screening,
        expected: tuple[Screening, ...],
    ) -> Screening:
        """Atomically persist the complete proposed row if checked state matches.

        Compare all stored Screening fields of every candidate and expected ID,
        ignoring joined parent metadata. Missing/changed rows, new candidates,
        or target/native-key collisions raise ScreeningWriteConflictError and
        commit nothing. Keep checked rows and uniqueness protected until commit.
        An existing ID must be present in expected; an absent ID is inserted.
        Implementations must neither evaluate source/day eligibility nor merge
        metadata. Callers reload and reevaluate after a conflict.
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

        Raises:
            ScreeningExternalIdConflictError: If the external ID belongs
                to a different screening.
        """
        ...

    @abstractmethod
    async def replace(
        self, screening: Screening, *, fields: frozenset[str]
    ) -> Screening:
        """Replace specified fields of a screening identified by ID.

        Args:
            screening: The screening with replacement values. The ID must
                match an existing row.
            fields: Explicitly supplied column names; omitted columns must be
                preserved atomically. An empty set returns the current entity
                without writing.

        Returns:
            The replaced screening entity.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
            ScreeningAlreadyExistsError: If the replacement identity
                collides with another screening.
            ScreeningExternalIdConflictError: If the external ID belongs to
                another screening.
        """
        ...

    @abstractmethod
    async def delete(self, screening_id: ScreeningId) -> bool:
        """Delete a screening and atomically remove its movie if now orphaned.

        Args:
            screening_id: The ID of the screening to delete.

        Returns:
            True if a screening was deleted, False if no screening with that
            ID exists.
        """
        ...

    @abstractmethod
    async def find_by_id(self, screening_id: ScreeningId) -> Screening:
        """Retrieve a screening by its unique identifier.

        Args:
            screening_id: The ID of the screening to find.

        Returns:
            The matching screening.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
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
