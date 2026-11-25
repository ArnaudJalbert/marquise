"""Adapter mapping screening display rows to application read models."""

from __future__ import annotations

from datetime import datetime

from marquise.application.page import Page
from marquise.application.readers import ScreeningReader
from marquise.interface_adapters.mappers import to_screening_data
from marquise.interface_adapters.readers.screening_read_gateway import (
    ScreeningReadGateway,
)


class PostgresScreeningReader(ScreeningReader):
    """Map projections supplied by an injected screening read gateway."""

    def __init__(self, gateway: ScreeningReadGateway) -> None:
        """Initialize with the plain-data gateway."""
        self._gateway = gateway

    async def find_by_id(
        self, screening_id: str
    ) -> ScreeningReader.ScreeningData | None:
        """Return one display projection for an exact ID, or None if missing."""
        row = await self._gateway.find_by_id(screening_id)
        return to_screening_data(row) if row is not None else None

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
        return Page(
            items=[to_screening_data(row) for row in page.rows], total=page.total
        )
