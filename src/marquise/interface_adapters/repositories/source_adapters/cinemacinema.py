"""Adapter for CinemaCinema source.

Translates a ``Cinema`` entity into the ``cinema_name`` slug expected
by ``CinemaCinemaSource``, then delegates scraping.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from marquise.domain.entities import Cinema
from marquise.interface_adapters.repositories.protocols.showtime_source import (
    ShowtimeSource,
)

_CINEMA_NAME_MAPPINGS: dict[str, str] = {
    "Cinéma Beaubien": "beaubien",
    "Cinéma du Parc": "du-parc",
    "Cinéma du Musée": "du-musee",
}


class CinemaCinemaAdapter:
    """Adapter that maps a Cinema entity to CinemaCinemaSource params.

    The underlying source expects a venue slug (``"beaubien"``,
    ``"du-parc"``, ``"du-musee"``).  This adapter maps the cinema's
    display name to the correct slug.

    Parameters
    ----------
    source:
        The ``CinemaCinemaSource`` instance to delegate to (injected).
    """

    def __init__(self, source: ShowtimeSource) -> None:
        self._source = source

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for a cinema from CinemaCinema.

        Args:
            cinema: The cinema entity to fetch for.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            A list of raw screening dicts.
        """
        venue = _CINEMA_NAME_MAPPINGS.get(cinema.name, cinema.name)
        return await self._source.fetch_showtimes(
            cinema_name=venue,
            start_date=start_date,
            end_date=end_date,
        )
