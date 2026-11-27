"""PostgreSQL implementation of CinemaSourceAssignmentGateway."""

from __future__ import annotations

import asyncpg

from marquise.interface_adapters.gateways.base import GatewayError

_COLUMNS = "cinema_id, source_name"
_CINEMA_COLUMNS = (
    "c.id AS cinema__id, c.name AS cinema__name,"
    " c.address AS cinema__address, c.city AS cinema__city,"
    " c.website AS cinema__website"
)
_SOURCE_COLUMNS = (
    "sd.name AS source__name, sd.display_name AS source__display_name,"
    " sd.description AS source__description"
)
_JOINED_COLUMNS = f"{_COLUMNS}, {_CINEMA_COLUMNS}, {_SOURCE_COLUMNS}"


class PostgresCinemaSourceAssignmentGateway:
    """Concrete assignment gateway backed by PostgreSQL.

    Args:
        pool: An open asyncpg connection pool.
        schema: The database schema where the cinema_source_assignments table
            lives.
    """

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        """Initialize the gateway.

        Args:
            pool: The asyncpg connection pool.
            schema: The database schema name.
        """
        self._pool = pool
        self._schema = schema
        self._table = f'"{schema}".cinema_source_assignments'

    async def assign(self, cinema_id: str, source_name: str) -> dict:
        """Upsert a cinema-source assignment.

        Args:
            cinema_id: The cinema identifier.
            source_name: The source name to assign.

        Returns:
            The upserted row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    f"""
                    INSERT INTO {self._table} (cinema_id, source_name)
                    VALUES ($1, $2)
                    ON CONFLICT (cinema_id) DO UPDATE SET source_name = $2
                    RETURNING {_COLUMNS}
                    """,
                    cinema_id,
                    source_name,
                )
            except Exception as exc:
                raise GatewayError(str(exc)) from exc
        return dict(row)

    async def unassign(self, cinema_id: str) -> bool:
        """Remove the source assignment for a cinema.

        Args:
            cinema_id: The cinema to unassign.

        Returns:
            True if a row was deleted, False if none existed.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table} WHERE cinema_id = $1",
                cinema_id,
            )
        return result != "DELETE 0"

    async def find_by_cinema_id(self, cinema_id: str) -> dict | None:
        """Find the source name assigned to a cinema.

        Args:
            cinema_id: The cinema identifier.

        Returns:
            A dict with joined cinema and source definition data,
            or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT {_JOINED_COLUMNS}
                FROM "{self._schema}".cinema_source_assignments a
                JOIN "{self._schema}".cinemas c ON a.cinema_id = c.id
                JOIN "{self._schema}".source_definitions sd
                    ON a.source_name = sd.name
                WHERE a.cinema_id = $1
                """,
                cinema_id,
            )
        return dict(row) if row is not None else None
