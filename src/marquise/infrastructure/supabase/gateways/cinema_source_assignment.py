"""Supabase PostgreSQL implementation of CinemaSourceAssignmentGateway."""

from __future__ import annotations

from typing import Optional

import asyncpg

from marquise.interface_adapters.repositories.protocols.cinema import GatewayError

DEFAULT_SCHEMA = "marquise"

_COLUMNS = "cinema_id, source_name"


class SupabaseCinemaSourceAssignmentGateway:
    """Concrete assignment gateway backed by Supabase PostgreSQL.

    Parameters
    ----------
    pool:
        An open asyncpg connection pool.
    schema:
        The database schema where the cinema_source_assignments table lives
        (default ``marquise``).
    """

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        """Initialize the gateway.

        Args:
            pool: The asyncpg connection pool.
            schema: The database schema name.
        """
        self._pool = pool
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

    async def find_by_cinema_id(self, cinema_id: str) -> Optional[dict]:
        """Find the source name assigned to a cinema.

        Args:
            cinema_id: The cinema identifier.

        Returns:
            A dict with keys ``cinema_id`` and ``source_name``, or None.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE cinema_id = $1",
                cinema_id,
            )
        return dict(row) if row is not None else None

    async def find_all(self) -> list[dict]:
        """Retrieve all cinema-source assignments.

        Returns:
            A list of dicts with keys ``cinema_id`` and ``source_name``.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM {self._table} ORDER BY cinema_id"
            )
        return [dict(r) for r in rows]
