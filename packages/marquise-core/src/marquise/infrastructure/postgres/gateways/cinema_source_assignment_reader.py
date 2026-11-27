"""PostgreSQL gateway for cinema-source assignment display projections."""

from __future__ import annotations

import asyncpg

_SELECT = "SELECT a.cinema_id, a.source_name, sd.display_name AS source_display_name"


class PostgresCinemaSourceAssignmentReadGateway:
    """Read plain assignment rows joined with source definitions from PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        """Initialize with an open connection pool and schema."""
        self._pool = pool
        self._schema = schema
        self._from = (
            f'FROM "{schema}".cinema_source_assignments a'
            f' JOIN "{schema}".source_definitions sd ON a.source_name = sd.name'
        )

    async def list_all(self) -> list[dict]:
        """Return every assignment row, ordered by cinema ID."""
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                f"{_SELECT} {self._from} ORDER BY a.cinema_id"
            )
        return [dict(row) for row in rows]

    async def find_by_cinema_id(self, cinema_id: str) -> dict | None:
        """Return one cinema's assignment row, or None when it has no source."""
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                f"{_SELECT} {self._from} WHERE a.cinema_id = $1", cinema_id
            )
        return dict(row) if row is not None else None
