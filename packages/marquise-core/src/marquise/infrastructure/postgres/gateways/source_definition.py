"""PostgreSQL implementation of SourceDefinitionGateway."""

from __future__ import annotations

import asyncpg

from marquise.interface_adapters.repositories.protocols.base import GatewayError

_COLUMNS = "name, display_name, description"


class PostgresSourceDefinitionGateway:
    """Concrete source definition gateway backed by PostgreSQL.

    Args:
        pool: An open asyncpg connection pool.
        schema: The database schema where the source_definitions table lives.
    """

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        """Initialize the gateway.

        Args:
            pool: The asyncpg connection pool.
            schema: The database schema name.
        """
        self._pool = pool
        self._table = f'"{schema}".source_definitions'

    async def save(
        self,
        name: str,
        display_name: str,
        description: str | None = None,
    ) -> dict:
        """Insert a source definition row.

        Args:
            name: Unique machine name.
            display_name: Human-readable label.
            description: Optional longer description.

        Returns:
            The inserted row as a dict.

        Raises:
            GatewayError: If a row with the given ``name`` already exists.
        """
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    f"""
                    INSERT INTO {self._table}
                        (name, display_name, description)
                    VALUES ($1, $2, $3)
                    RETURNING {_COLUMNS}
                    """,
                    name,
                    display_name,
                    description,
                )
            except asyncpg.exceptions.UniqueViolationError:
                raise GatewayError(
                    f"A source with name '{name}' already exists"
                ) from None
        return dict(row)

    async def find_by_name(self, name: str) -> dict | None:
        """Find a source definition by its name.

        Args:
            name: The unique machine name to look up.

        Returns:
            A dict representing the row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE name = $1",
                name,
            )
        return dict(row) if row is not None else None

    async def find_all(self) -> list[dict]:
        """Retrieve all source definition rows.

        Returns:
            A list of dicts representing source definition rows.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM {self._table} ORDER BY name"
            )
        return [dict(r) for r in rows]

    async def delete(self, name: str) -> bool:
        """Delete a source definition by name.

        Args:
            name: The machine name of the source to delete.

        Returns:
            True if a row was deleted, False otherwise.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table} WHERE name = $1",
                name,
            )
        return result != "DELETE 0"
