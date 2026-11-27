"""Adapter for Cinéma Moderne source.

Cinéma Moderne is a single-venue source, so this adapter simply delegates
to the underlying ``CinemaModerneSource`` without any per-cinema parameter
translation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from marquise.domain.entities import Cinema
from marquise.interface_adapters.gateways.showtime_source import (
    ShowtimeSource,
)


class CinemaModerneAdapter:
    """Adapter that delegates to CinemaModerneSource (single venue, no mapping needed).

    Parameters
    ----------
    source:
        The ``CinemaModerneSource`` instance to delegate to (injected).
    """

    def __init__(self, source: ShowtimeSource) -> None:
        self._source = source

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for Cinéma Moderne.

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
        """Fetch enriched movie metadata from Cinéma Moderne.

        Args:
            identifier: The film detail page URL, as returned in a showtime
                row's ``identifier`` field.

        Returns:
            A raw dict of movie metadata, or ``None``.
        """
        return await self._source.fetch_movie_detail(identifier=identifier)
