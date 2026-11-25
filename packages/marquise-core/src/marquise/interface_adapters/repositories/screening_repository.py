"""Postgres repository implementation of ScreeningRepository.

Adapts a ``ScreeningGateway`` (infrastructure) into the ``ScreeningRepository``
interface (application).  No SQL, no asyncpg — pure entity mapping.
"""

from __future__ import annotations

from datetime import UTC, datetime

from marquise.application.exceptions import (
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningNotFoundError,
)
from marquise.application.exceptions.screening import ScreeningWriteConflictError
from marquise.application.page import Page
from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    ScreeningId,
    Showtime,
)
from marquise.interface_adapters.mappers import (
    extract_prefixed,
    to_cinema,
    to_movie,
)
from marquise.interface_adapters.repositories.protocols.base import GatewayError
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningExternalIdConflictGatewayError,
    ScreeningGateway,
    ScreeningWriteConflictGatewayError,
)


def _parse_datetime(value: datetime) -> datetime:
    """Normalize a gateway datetime to a timezone-aware UTC datetime.

    The screening gateway always returns ``datetime`` objects from asyncpg.
    Naive values are assumed to be in UTC and made timezone-aware.

    Args:
        value: A datetime object returned by the gateway.

    Returns:
        A timezone-aware datetime.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class PostgresScreeningRepository(ScreeningRepository):
    """Screening repository backed by a PostgreSQL database.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``ScreeningGateway``.
    """

    def __init__(self, gateway: ScreeningGateway) -> None:
        self._gateway = gateway

    async def save(self, screening: Screening) -> Screening:
        """Persist a screening via the gateway and return the mapped entity.

        Args:
            screening: The screening domain entity to save.

        Returns:
            The saved screening entity.

        Raises:
            ScreeningAlreadyExistsError: If a screening with the same
                (cinema_id, movie_id, showtime) already exists.
            ScreeningExternalIdConflictError: If the external ID belongs
                to a different screening.
        """
        try:
            outcome = await self._gateway.save(
                screening_id=str(screening.id),
                movie_id=str(screening.movie.id),
                cinema_id=str(screening.cinema.id),
                showtime=screening.showtime.value,
                external_id=screening.external_id,
                source_name=screening.source_name,
                ticket_url=screening.ticket_url,
                room=screening.room,
                language=screening.language,
            )
        except ScreeningExternalIdConflictGatewayError as exc:
            raise ScreeningExternalIdConflictError(str(exc)) from exc
        if not outcome.inserted:
            raise ScreeningAlreadyExistsError(
                f"A screening already exists for cinema '{screening.cinema.id}'"
                f", movie '{screening.movie.id}' at {screening.showtime.value}"
            )
        return Screening(
            id=ScreeningId(value=outcome.row["id"]),
            movie=screening.movie,
            cinema=screening.cinema,
            showtime=Showtime(value=_parse_datetime(outcome.row["showtime"])),
            external_id=outcome.row.get("external_id"),
            source_name=outcome.row.get("source_name"),
            ticket_url=outcome.row.get("ticket_url"),
            room=outcome.row.get("room"),
            language=outcome.row.get("language"),
        )

    async def read_import_candidates(
        self, incoming: Screening
    ) -> tuple[Screening, ...]:
        """Map all native-key and target-identity candidates to detached entities."""
        rows = await self._gateway.read_import_candidates(
            cinema_id=str(incoming.cinema.id),
            movie_id=str(incoming.movie.id),
            showtime=incoming.showtime.value,
            external_id=incoming.external_id,
        )
        return tuple(self._to_entity(row) for row in rows)

    async def commit_import(
        self,
        proposed: Screening,
        *,
        incoming: Screening,
        expected: tuple[Screening, ...],
    ) -> Screening:
        """Map the complete decision and checked state to persistence data."""
        try:
            row = await self._gateway.commit_import(
                _persistence_data(proposed),
                incoming=_persistence_data(incoming),
                expected=tuple(_persistence_data(row) for row in expected),
            )
        except ScreeningWriteConflictGatewayError as exc:
            raise ScreeningWriteConflictError(str(exc)) from exc
        return self._to_entity(row)

    async def replace(
        self, screening: Screening, *, fields: frozenset[str]
    ) -> Screening:
        """Replace specified fields of a screening identified by ID.

        Args:
            screening: The screening with replacement values.
            fields: Explicitly supplied columns; an empty set returns the current entity
                without writing.

        Returns:
            The persisted screening entity, including its current parents.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
            ScreeningAlreadyExistsError: If the replacement identity
                collides with another screening.
            ScreeningExternalIdConflictError: If the external ID belongs to
                another screening.
        """
        try:
            data = await self._gateway.replace(
                screening_id=str(screening.id),
                movie_id=str(screening.movie.id),
                cinema_id=str(screening.cinema.id),
                showtime=screening.showtime.value,
                external_id=screening.external_id,
                ticket_url=screening.ticket_url,
                room=screening.room,
                language=screening.language,
                fields=fields,
            )
        except ScreeningExternalIdConflictGatewayError as exc:
            raise ScreeningExternalIdConflictError(str(exc)) from exc
        except GatewayError as exc:
            raise ScreeningAlreadyExistsError(str(exc)) from exc
        if data is None:
            raise ScreeningNotFoundError(
                f"A screening with ID '{screening.id}' was not found"
            )
        return self._to_entity(data)

    async def delete(self, screening_id: ScreeningId) -> bool:
        """Delete a screening and atomically remove its movie if now orphaned.

        Args:
            screening_id: The ID of the screening to delete.

        Returns:
            True if a screening was deleted, False otherwise.
        """
        return await self._gateway.delete(screening_id=str(screening_id))

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
            distinct movies matching the cinema and date range.
        """
        gateway_page = await self._gateway.find_distinct_movies_by_cinema(
            cinema_id=str(cinema_id),
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return Page(
            items=[to_movie(row) for row in gateway_page.rows],
            total=gateway_page.total,
        )

    @staticmethod
    def _to_entity(data: dict) -> Screening:
        """Map a raw gateway dict to a Screening domain entity.

        Args:
            data: The dict returned by the gateway (with joined movie and
                cinema data prefixed with ``movie__`` and ``cinema__``).

        Returns:
            A new Screening entity populated with the dict values.
        """
        movie = to_movie(extract_prefixed(data, "movie__"))
        cinema = to_cinema(extract_prefixed(data, "cinema__"))
        return Screening(
            id=ScreeningId(value=data["id"]),
            movie=movie,
            cinema=cinema,
            showtime=Showtime(value=_parse_datetime(data["showtime"])),
            external_id=data.get("external_id"),
            source_name=data.get("source_name"),
            ticket_url=data.get("ticket_url"),
            room=data.get("room"),
            language=data.get("language"),
        )


def _persistence_data(screening: Screening) -> dict:
    """Map stored Screening columns, excluding joined parent metadata."""
    return {
        "id": str(screening.id),
        "movie_id": str(screening.movie.id),
        "cinema_id": str(screening.cinema.id),
        "showtime": screening.showtime.value.astimezone(UTC).replace(tzinfo=None),
        "external_id": screening.external_id,
        "source_name": screening.source_name,
        "ticket_url": screening.ticket_url,
        "room": screening.room,
        "language": screening.language,
    }
