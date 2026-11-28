"""PostgreSQL gateway for cinema display projections."""

from __future__ import annotations

import asyncpg

from marquise.interface_adapters.gateways.base import GatewayPage

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

    async def search(
        self, name_filter: str | None, limit: int, offset: int
    ) -> GatewayPage:
        """Return one page of display rows ordered by name, plus the true total.

        Args:
            name_filter: Optional case-insensitive substring of the name.
            limit: Max number of rows to return.
            offset: Number of matching rows to skip.

        Returns:
            The page of rows and the count of every row matching the filter.
        """
        table = f'"{self._schema}".cinemas'
        where_clause = "WHERE LOWER(name) LIKE LOWER($1)" if name_filter else ""
        params: list = [f"%{name_filter}%"] if name_filter else []
        async with self._pool.acquire() as connection:
            # COUNT(*) OVER() rides along with the page, so a non-empty page
            # costs one round trip. An empty page has no row to read it off,
            # so that case falls back to a separate COUNT(*).
            rows = await connection.fetch(
                f"""
                SELECT {_COLUMNS}, COUNT(*) OVER() AS __total
                FROM {table}
                {where_clause}
                ORDER BY name
                LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
                """,
                *params,
                limit,
                offset,
            )
            if not rows:
                total = await connection.fetchval(
                    f"SELECT COUNT(*) FROM {table} {where_clause}", *params
                )
                return GatewayPage(rows=[], total=total)
        result_rows = [dict(row) for row in rows]
        for row in result_rows:
            row.pop("__total")
        return GatewayPage(rows=result_rows, total=rows[0]["__total"])
