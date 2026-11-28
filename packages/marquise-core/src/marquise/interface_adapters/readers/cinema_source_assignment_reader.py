"""Adapter mapping cinema-source assignment rows to application read models."""

from __future__ import annotations

from marquise.application.readers import CinemaSourceAssignmentReader
from marquise.interface_adapters.gateways.cinema_source_assignment_reader import (
    CinemaSourceAssignmentReadGateway,
)


class PostgresCinemaSourceAssignmentReader(CinemaSourceAssignmentReader):
    """Map projections supplied by an injected assignment read gateway."""

    def __init__(self, gateway: CinemaSourceAssignmentReadGateway) -> None:
        """Initialize with the plain-data gateway."""
        self._gateway = gateway

    async def list_all(
        self,
    ) -> list[CinemaSourceAssignmentReader.CinemaSourceAssignmentData]:
        """Return every cinema-source assignment's display data."""
        return [
            self.CinemaSourceAssignmentData(**row)
            for row in await self._gateway.list_all()
        ]

    async def find_by_cinema_id(
        self, cinema_id: str
    ) -> CinemaSourceAssignmentReader.CinemaSourceAssignmentData | None:
        """Return one cinema's assignment, or None when it has no source."""
        row = await self._gateway.find_by_cinema_id(cinema_id)
        return self.CinemaSourceAssignmentData(**row) if row is not None else None
