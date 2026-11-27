"""PostgreSQL gateway for source definition display rows."""

from __future__ import annotations

import asyncpg


class PostgresSourceDefinitionReadGateway:
    """Read plain source definition rows from PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        """Initialize with an open connection pool and schema."""
        self._pool = pool
        self._schema = schema

    async def list_all(self) -> list[dict]:
        """Return every source definition row, ordered by name."""
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                f"""
                SELECT name, display_name, description
                FROM "{self._schema}".source_definitions
                ORDER BY name
                """
            )
        return [dict(row) for row in rows]
