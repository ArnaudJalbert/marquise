"""Map plain movie-card rows to application read models."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.application.repositories.page import Page
from marquise.interface_adapters.readers.screening_reader import _to_data
from marquise.interface_adapters.repositories.protocols.base import GatewayPage


class ScreeningMovieReadGateway(Protocol):
    """Plain-data contract for distinct-movie pagination."""

    async def search(
        self, start: datetime, end: datetime, now: datetime, page: int
    ) -> GatewayPage:
        """Return 24 distinct movies with ordered previews and a true total."""
        ...


class SupabaseScreeningMovieReader(ScreeningMovieReader):
    """Adapt an injected gateway without database I/O of its own."""

    def __init__(self, gateway: ScreeningMovieReadGateway) -> None:
        """Inject the plain-data gateway."""
        self._gateway = gateway

    async def search(
        self, start: datetime, end: datetime, now: datetime, page: int
    ) -> Page[ScreeningMovieReader.MovieData]:
        """Map movie metadata and screening projections."""
        result = await self._gateway.search(start, end, now, page)
        return Page(
            items=[
                self.MovieData(
                    id=row["id"],
                    title=row["title"],
                    release_year=row["release_year"],
                    directors=tuple(row["directors"].split(","))
                    if row["directors"]
                    else None,
                    duration_minutes=row["duration_minutes"],
                    description=row["description"],
                    poster_url=row["poster_url"],
                    screenings=tuple(_to_data(s) for s in row["screenings"]),
                )
                for row in result.rows
            ],
            total=result.total,
        )
