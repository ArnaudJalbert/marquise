"""Gateway contract for cinema display projections."""

from __future__ import annotations

from typing import Protocol

from marquise.interface_adapters.gateways.base import GatewayPage


class CinemaReadGateway(Protocol):
    """Read plain cinema projections without hydrating domain entities."""

    async def find_by_id(self, cinema_id: str) -> dict | None:
        """Return the display row for an exact ID, or None when missing."""
        ...

    async def search(
        self, name_filter: str | None, limit: int, offset: int
    ) -> GatewayPage:
        """Return one page of display rows ordered by name, plus the true total.

        A name filter matches a case-insensitive substring of the name.
        """
        ...
