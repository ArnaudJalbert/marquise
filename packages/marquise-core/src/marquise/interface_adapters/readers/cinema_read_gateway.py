"""Gateway contract for cinema display projections."""

from __future__ import annotations

from typing import Protocol


class CinemaReadGateway(Protocol):
    """Read plain cinema projections without hydrating domain entities."""

    async def find_by_id(self, cinema_id: str) -> dict | None:
        """Return the display row for an exact ID, or None when missing."""
        ...
