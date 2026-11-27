"""Adapter for Cinémathèque québécoise source.

Cinémathèque québécoise is a single-venue source, so this adapter simply
delegates to the underlying ``CinemathequeSource`` without any per-cinema
parameter translation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from marquise.domain.entities import Cinema
from marquise.interface_adapters.gateways.showtime_source import (
    ShowtimeSource,
)


class CinemathequeAdapter:
    """Adapter that delegates to CinemathequeSource (single venue, no mapping needed).

    Parameters
    ----------
    source:
        The ``CinemathequeSource`` instance to delegate to (injected).
    """

    def __init__(self, source: ShowtimeSource) -> None:
        self._source = source

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for Cinémathèque québécoise.

        Args:
            cinema: The cinema entity to fetch for (unused — single venue).
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            A list of raw screening dicts.
        """
        return await self._source.fetch_showtimes(
            start_date=start_date,
            end_date=end_date,
        )

    async def fetch_movie_detail(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        """Fetch enriched movie metadata from Cinémathèque québécoise.

        Args:
            identifier: A ``"YYYY-MM-DD|<film code>"`` string, as returned in
                a showtime row's ``identifier`` field.

        Returns:
            A raw dict of movie metadata, or ``None``.
        """
        return await self._source.fetch_movie_detail(identifier=identifier)
