"""Adapter mapping screening display rows to application read models."""

from __future__ import annotations

from datetime import UTC, datetime

from marquise.application.page import Page
from marquise.application.readers import ScreeningReader
from marquise.interface_adapters.readers.screening_read_gateway import (
    ScreeningReadGateway,
)


def _aware_utc(value: datetime) -> datetime:
    """Treat naive database timestamps as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_data(row: dict) -> ScreeningReader.ScreeningData:
    """Map a display row without hydrating movie or cinema entities."""
    return ScreeningReader.ScreeningData(
        id=row["id"],
        movie_id=row["movie_id"],
        movie_title=row["movie_title"],
        cinema_id=row["cinema_id"],
        cinema_name=row["cinema_name"],
        showtime=_aware_utc(row["showtime"]),
        ticket_url=row.get("ticket_url"),
        room=row.get("room"),
        language=row.get("language"),
    )


class SupabaseScreeningReader(ScreeningReader):
    """Map projections supplied by an injected screening read gateway."""

    def __init__(self, gateway: ScreeningReadGateway) -> None:
        """Initialize with the plain-data gateway."""
        self._gateway = gateway

    async def find_by_id(
        self, screening_id: str
    ) -> ScreeningReader.ScreeningData | None:
        """Return one display projection for an exact ID, or None if missing."""
        row = await self._gateway.find_by_id(screening_id)
        return _to_data(row) if row is not None else None

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
    ) -> Page[ScreeningReader.ScreeningData]:
        """Return screenings matching optional filters, paginated."""
        page = await self._gateway.search(
            movie_id=movie_id,
            movie_title=movie_title,
            cinema_id=cinema_id,
            start_date=start_date,
            end_date=end_date,
            language=language,
            limit=limit,
            offset=offset,
        )
        return Page(items=[_to_data(row) for row in page.rows], total=page.total)
