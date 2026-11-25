"""Gateway contract for distinct-movie screening projections."""

from __future__ import annotations

from typing import Protocol

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.interface_adapters.gateways.base import GatewayPage


class ScreeningMovieReadGateway(Protocol):
    """Plain-data contract for distinct-movie pagination."""

    async def search(self, request: ScreeningMovieReader.SearchRequest) -> GatewayPage:
        """Return 24 distinct movies with ordered previews and a true total."""
        ...

    async def count_days(
        self, request: ScreeningMovieReader.DayCountRequest
    ) -> list[dict]:
        """Return one ``day`` and ``screenings`` row per non-empty Montréal date."""
        ...
