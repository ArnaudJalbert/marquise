"""Adapter mapping cinema display rows to application read models."""

from __future__ import annotations

from marquise.application.page import Page
from marquise.application.readers import CinemaReader
from marquise.interface_adapters.mappers import to_cinema_data
from marquise.interface_adapters.readers.cinema_read_gateway import (
    CinemaReadGateway,
)


class PostgresCinemaReader(CinemaReader):
    """Map projections supplied by an injected cinema read gateway."""

    def __init__(self, gateway: CinemaReadGateway) -> None:
        """Initialize with the plain-data gateway."""
        self._gateway = gateway

    async def find_by_id(self, cinema_id: str) -> CinemaReader.CinemaData | None:
        """Return one display projection for an exact ID, or None if missing."""
        row = await self._gateway.find_by_id(cinema_id)
        return to_cinema_data(row) if row is not None else None

    async def search(
        self, name_filter: str | None, limit: int, offset: int
    ) -> Page[CinemaReader.CinemaData]:
        """Return one page of cinemas ordered by name, plus the true total."""
        page = await self._gateway.search(
            name_filter=name_filter, limit=limit, offset=offset
        )
        return Page(items=[to_cinema_data(row) for row in page.rows], total=page.total)
