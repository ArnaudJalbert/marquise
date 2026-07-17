"""Adapter for Cinema Public source.

Translates a ``Cinema`` entity into the ``cinema_name`` param expected
by ``CinemaPublicSource``, then delegates scraping.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from marquise.domain.entities import Cinema
from marquise.interface_adapters.repositories.protocols.showtime_source import (
    ShowtimeSource,
)

_CINEMA_NAME_MAPPINGS: dict[str, str] = {
    "Cinéma Public": "casa-d-italia",
    "Cinema Public — Casa d'Italia": "casa-d-italia",
    "Cinema Public — Livart": "livart",
}


class CinemaPublicAdapter:
    """Adapter that maps a Cinema entity to CinemaPublicSource params.

    The underlying source expects a venue slug (``"casa-d-italia"``,
    ``"livart"``).  This adapter maps the cinema's display name to the
    correct slug.

    Parameters
    ----------
    source:
        The ``CinemaPublicSource`` instance to delegate to (injected).
    """

    def __init__(self, source: ShowtimeSource) -> None:
        self._source = source

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for a cinema from Cinema Public.

        Args:
            cinema: The cinema entity to fetch for.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            A list of raw screening dicts.
        """
        try:
            venue = _CINEMA_NAME_MAPPINGS[cinema.name]
        except KeyError:
            valid = ", ".join(sorted(_CINEMA_NAME_MAPPINGS))
            raise ValueError(
                f"Unknown Cinema Public venue: '{cinema.name}'. "
                f"Valid cinema names: {valid}"
            ) from None
        return await self._source.fetch_showtimes(
            cinema_name=venue,
            start_date=start_date,
            end_date=end_date,
        )

    async def fetch_movie_detail(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        """Fetch enriched movie metadata from Cinema Public.

        Args:
            identifier: The film detail page URL
                (e.g. ``"https://cinemapublic.ca/en/films/kairos/"``).

        Returns:
            A raw dict of movie metadata, or ``None``.
        """
        return await self._source.fetch_movie_detail(movie_url=identifier)
