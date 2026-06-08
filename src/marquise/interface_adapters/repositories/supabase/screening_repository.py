"""Supabase repository implementation of ScreeningRepository.

Adapts a ``ScreeningGateway`` (infrastructure) into the ``ScreeningRepository``
interface (application).  No SQL, no asyncpg — pure entity mapping.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    Price,
    ScreeningId,
    Showtime,
)
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningGateway,
)


def _parse_datetime(value: datetime | str) -> datetime:
    """Parse a datetime value, accepting both datetime objects and ISO strings.

    Args:
        value: A datetime object or a datetime string (ISO or 12-hour AM/PM).

    Returns:
        A parsed datetime object.
    """
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%dT%I:%M %p")


class SupabaseScreeningRepository(ScreeningRepository):
    """Screening repository backed by a Supabase PostgreSQL database.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``ScreeningGateway``.
    """

    def __init__(self, gateway: ScreeningGateway) -> None:
        self._gateway = gateway

    async def save(self, screening: Screening) -> tuple[Screening, bool]:
        """Persist a screening via the gateway and return the mapped entity.

        Args:
            screening: The screening domain entity to save.

        Returns:
            A tuple of (saved_screening, was_inserted).
        """
        data = await self._gateway.save(
            screening_id=str(screening.id),
            movie_id=str(screening.movie_id),
            cinema_id=str(screening.cinema_id),
            showtime=screening.showtime.value,
            price=screening.price.value,
        )
        was_inserted = data.pop("__inserted", True)
        return self._to_entity(data), was_inserted

    async def find_by_id(self, screening_id: ScreeningId) -> Optional[Screening]:
        """Retrieve a screening by ID.

        Args:
            screening_id: The unique identifier of the screening.

        Returns:
            The matching screening entity, or None if not found.
        """
        data = await self._gateway.find_by_id(screening_id=str(screening_id))
        return self._to_entity(data) if data is not None else None

    async def find_by_cinema_and_date_range(
        self,
        cinema_id: CinemaId,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Screening]:
        """Find screenings for a cinema within a date range.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).

        Returns:
            A list of matching screening entities.
        """
        rows = await self._gateway.find_by_cinema_and_date_range(
            cinema_id=str(cinema_id),
            start_date=start_date,
            end_date=end_date,
        )
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(data: dict) -> Screening:
        """Map a raw gateway dict to a Screening domain entity.

        Args:
            data: The dict returned by the gateway.

        Returns:
            A new Screening entity populated with the dict values.
        """
        return Screening(
            id=ScreeningId(value=data["id"]),
            movie_id=MovieId(value=data["movie_id"]),
            cinema_id=CinemaId(value=data["cinema_id"]),
            showtime=Showtime(
                value=_parse_datetime(data["showtime"]),
            ),
            price=Price(value=float(data["price"])),
        )
