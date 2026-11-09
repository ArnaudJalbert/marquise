"""Map plain movie-card rows to application read models."""

from __future__ import annotations

from typing import Protocol

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.application.repositories.page import Page
from marquise.interface_adapters.readers.screening_reader import _to_data
from marquise.interface_adapters.repositories.protocols.base import GatewayPage


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


class SupabaseScreeningMovieReader(ScreeningMovieReader):
    """Adapt an injected gateway without database I/O of its own."""

    def __init__(self, gateway: ScreeningMovieReadGateway) -> None:
        """Inject the plain-data gateway."""
        self._gateway = gateway

    async def search(
        self, request: ScreeningMovieReader.SearchRequest
    ) -> Page[ScreeningMovieReader.MovieData]:
        """Map movie metadata and screening projections."""
        result = await self._gateway.search(request)
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
                    tmdb_rating=row["tmdb_rating"],
                    tmdb_vote_count=row["tmdb_vote_count"],
                    screenings=tuple(_to_data(s) for s in row["screenings"]),
                )
                for row in result.rows
            ],
            total=result.total,
        )

    async def count_days(
        self, request: ScreeningMovieReader.DayCountRequest
    ) -> list[ScreeningMovieReader.DayCount]:
        """Map daily screening totals."""
        rows = await self._gateway.count_days(request)
        return [self.DayCount(row["day"], row["screenings"]) for row in rows]
