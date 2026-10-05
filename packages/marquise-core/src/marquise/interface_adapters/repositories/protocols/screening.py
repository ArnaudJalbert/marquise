"""Screening data gateway protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from marquise.interface_adapters.repositories.protocols.base import (
    GatewayError,
    GatewayPage,
)


class ScreeningExternalIdConflictGatewayError(GatewayError):
    """Raised when an external ID conflicts with another screening row."""


@dataclass(frozen=True, slots=True)
class SaveOutcome:
    """Result of a screening save, distinguishing insert from match.

    Attributes:
        row: The inserted or existing screening row as a plain dict.
        inserted: ``True`` if a new row was created, ``False`` if an existing
            row was matched on the unique constraint.
    """

    row: dict
    inserted: bool


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
        external_id: str | None = None,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
    ) -> SaveOutcome:
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
            A ``SaveOutcome`` carrying the inserted or existing row and whether
            a new row was created.

        Raises:
            ScreeningExternalIdConflictGatewayError: If the external ID
                belongs to another screening.
            GatewayError: On other data-layer failure.
        """
        ...

    async def update(
        self,
        cinema_id: str,
        movie_id: str,
        showtime: datetime,
        external_id: str | None = None,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
    ) -> dict | None:
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

        Raises:
            ScreeningExternalIdConflictGatewayError: If the external ID
                belongs to another screening.
        """
        ...

    async def replace(
        self,
        screening_id: str,
        movie_id: str,
        cinema_id: str,
        showtime: datetime,
        external_id: str | None = None,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
        *,
        fields: frozenset[str],
    ) -> dict | None:
        """Replace specified fields of a screening identified by ID.

        Args:
            screening_id: The unique identifier of the row to replace.
            movie_id: Replacement movie ID.
            cinema_id: Replacement cinema ID.
            showtime: Replacement screening time.
            external_id: Replacement source-native key (optional).
            ticket_url: Replacement ticket URL (optional).
            room: Replacement room name (optional).
            language: Replacement language (optional).
            fields: Explicitly supplied columns; an empty set reads the current row
                without writing.

        Returns:
            The updated row with joined movie and cinema data, or None if missing.

        Raises:
            ScreeningExternalIdConflictGatewayError: If the external ID belongs
                to another screening.
            GatewayError: If the screening identity collides with another row.
        """
        ...

    async def delete(self, screening_id: str) -> None:
        """Delete a screening and atomically remove its movie if now orphaned.

        Args:
            screening_id: The unique identifier of the row to delete.

        Raises:
            GatewayError: If no row has the given ID.
        """
        ...

    async def find_by_id(self, screening_id: str) -> dict | None:
        """Find a screening by its ID.

        Args:
            screening_id: The unique identifier.

        Returns:
            A dict representing the row, or None.
        """
        ...

    async def search(
        self,
        movie_id: str | None = None,
        movie_title: str | None = None,
        cinema_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        language: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
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
            limit: Max number of rows to return. If None, all matching rows
                are returned unbounded.
            offset: Number of matching rows to skip before returning results.

        Returns:
            A ``GatewayPage`` with the matching rows (joined with movie and
            cinema data) and the total count of rows matching the filters,
            ignoring ``limit``/``offset``.
        """
        ...

    async def find_distinct_movies_by_cinema(
        self,
        cinema_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
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
            A ``GatewayPage`` with the matching movie rows (plain movie
            columns, not prefixed) and the total count of distinct movies
            matching the cinema and date range, ignoring ``limit``/``offset``.
        """
        ...
