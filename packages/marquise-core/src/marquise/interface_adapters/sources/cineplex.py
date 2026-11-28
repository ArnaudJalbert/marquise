"""Adapter for Cineplex source.

Translates a ``Cinema`` entity into the ``location_id`` parameter
expected by ``CineplexSource``, then delegates scraping.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from marquise.domain.entities import Cinema
from marquise.interface_adapters.gateways.showtime_source import (
    ShowtimeSource,
)

_CINEMA_LOCATION_MAPPINGS: dict[str, int] = {
    "Cin\u00e9ma Starcit\u00e9 Montr\u00e9al": 9401,
    "Cin\u00e9ma Cineplex Odeon Quartier Latin": 9172,
    "Cin\u00e9ma Banque Scotia Montr\u00e9al": 9406,
    "Scotiabank Cinema Montreal": 9406,
    "Cin\u00e9ma Cineplex Forum et VIP": 9109,
    "Cin\u00e9ma Famous Players Carrefour Angrignon": 9195,
    "Cin\u00e9ma Cineplex Laval": 9408,
    "Cin\u00e9ma Cineplex Odeon Saint-Bruno": 9143,
    "Cin\u00e9ma Cineplex Odeon Brossard et VIP": 9185,
    "Cin\u00e9ma Cineplex Kirkland": 9407,
    "Cin\u00e9ma Cineplex Royalmount": 9121,
}


class CineplexAdapter:
    """Adapter that maps a Cinema entity to CineplexSource params.

    The underlying source expects a numeric ``location_id`` (theatre ID).
    This adapter maps the cinema's display name to the correct Cineplex
    theatre ID.

    Parameters
    ----------
    source:
        The ``CineplexSource`` instance to delegate to (injected).
    """

    def __init__(self, source: ShowtimeSource) -> None:
        self._source = source

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for a cinema from Cineplex.

        Args:
            cinema: The cinema entity to fetch for.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            A list of raw screening dicts.

        Raises:
            ValueError: If the cinema name is not mapped to a known
                Cineplex theatre ID.
        """
        location_id = _CINEMA_LOCATION_MAPPINGS.get(cinema.name)
        if location_id is None:
            raise ValueError(
                f"No Cineplex location ID mapping for cinema '{cinema.name}'"
            )
        rows = await self._source.fetch_showtimes(
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
        )
        # Cineplex lists the same showtime under multiple experiences
        # (e.g. standard + IMAX), producing duplicate (movie_title, showtime)
        # pairs that would race on the DB unique constraint when upserted
        # concurrently. Keep the first occurrence of each pair.
        #
        # Cineplex also occasionally lists the same underlying session
        # (identical external_id / vista session ID) under two different
        # movie titles, which the (movie_title, showtime) key above would
        # not catch and which would instead violate the DB's unique
        # constraint on external_id. Dedupe on external_id first whenever
        # it looks like a real session ID (source falls back to 0 when
        # missing).
        seen_external_ids: set[str] = set()
        seen_pairs: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            external_id = row.get("external_id")
            if external_id and external_id != "0":
                if external_id in seen_external_ids:
                    continue
                seen_external_ids.add(external_id)
            else:
                pair = (row["movie_title"], row["showtime"])
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
            deduped.append(row)
        return deduped

    async def fetch_movie_detail(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        """Fetch enriched movie metadata from Cineplex.

        Args:
            identifier: The film slug (e.g. ``"the-odyssey"``).

        Returns:
            A raw dict of movie metadata, or ``None``.
        """
        return await self._source.fetch_movie_detail(slug=identifier)
