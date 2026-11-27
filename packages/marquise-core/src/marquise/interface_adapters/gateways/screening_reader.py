"""Gateway contract for screening display projections."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from marquise.interface_adapters.gateways.base import GatewayPage


class ScreeningReadGateway(Protocol):
    """Read plain screening projections without hydrating domain entities."""

    async def find_by_id(self, screening_id: str) -> dict | None:
        """Return the display row for an exact ID, or None when missing."""
        ...

    async def search(
        self,
        movie_id: str | None = None,
        movie_title: str | None = None,
        cinema_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        language: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
        """Return display rows ordered by showtime and ID, plus the true total.

        Date bounds are inclusive. Titles match case-insensitive substrings.
        Without a limit, return all matching rows; otherwise apply limit/offset.
        """
        ...
