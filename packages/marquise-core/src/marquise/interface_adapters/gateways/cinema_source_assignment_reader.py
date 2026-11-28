"""Gateway contract for cinema-source assignment display projections."""

from __future__ import annotations

from typing import Protocol


class CinemaSourceAssignmentReadGateway(Protocol):
    """Read plain assignment rows joined with their source definitions.

    Each row has ``cinema_id``, ``source_name`` and ``source_display_name``.
    """

    async def list_all(self) -> list[dict]:
        """Return every assignment row, ordered by cinema ID."""
        ...

    async def find_by_cinema_id(self, cinema_id: str) -> dict | None:
        """Return one cinema's assignment row, or None when it has no source."""
        ...
