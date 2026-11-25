"""PostgreSQL gateway for cinema display projections."""

from __future__ import annotations

import asyncpg

_COLUMNS = "id, name, address, city, website"


class PostgresCinemaReadGateway:
    """Read plain cinema display rows from PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        """Initialize with an open connection pool and schema."""
        self._pool = pool
        self._schema = schema

    async def find_by_id(self, cinema_id: str) -> dict | None:
        """Return one display row for an exact ID, or None if missing."""
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                f'SELECT {_COLUMNS} FROM "{self._schema}".cinemas WHERE id = $1',
                cinema_id,
            )
        return dict(row) if row is not None else None
