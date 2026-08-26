"""Adapter for Cine Starz source."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from marquise.domain.entities import Cinema
from marquise.interface_adapters.repositories.protocols.showtime_source import (
    ShowtimeSource,
)

_CINEMA_VENUE_MAPPINGS: dict[str, str] = {
    "Ciné Starz Côte-des-Neiges": "CotedesNeiges",
    "Ciné Starz Deluxe Cavendish": "DeluxeCavendish",
}


class CineStarzAdapter:
    """Map Cine Starz cinema names to venue keys and delegate to source."""

    def __init__(self, source: ShowtimeSource) -> None:
        """Store injected Cine Starz source gateway."""
        self._source = source

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for mapped Cine Starz cinema.

        Raises:
            ValueError: If cinema name has no Cine Starz venue mapping.
        """
        venue_key = _CINEMA_VENUE_MAPPINGS.get(cinema.name)
        if venue_key is None:
            raise ValueError(f"No Cine Starz venue mapping for cinema '{cinema.name}'")
        return await self._source.fetch_showtimes(
            venue_key=venue_key,
            start_date=start_date,
            end_date=end_date,
        )

    async def fetch_movie_detail(self, identifier: str) -> dict[str, Any] | None:
        """Fetch movie metadata from Cine Starz.

        Args:
            identifier: Absolute Cine Starz movie page URL.
        """
        return await self._source.fetch_movie_detail(identifier=identifier)
