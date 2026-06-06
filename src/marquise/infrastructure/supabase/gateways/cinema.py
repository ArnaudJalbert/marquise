"""Supabase PostgreSQL implementation of CinemaGateway."""

from __future__ import annotations

from typing import Optional

import asyncpg

from marquise.interface_adapters.repositories.protocols.cinema import GatewayError

DEFAULT_SCHEMA = "marquise"


class SupabaseCinemaGateway:
    """Concrete cinema gateway that executes SQL against Supabase PostgreSQL.

    Parameters
    ----------
    pool:
        An open asyncpg connection pool.
    schema:
        The database schema where the cinemas table lives (default ``marquise``).
    """

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        """Initialize the gateway.

        Args:
            pool: The asyncpg connection pool.
            schema: The database schema name.
        """
        self._pool = pool
        self._table = f'"{schema}".cinemas'

    async def save(
        self, cinema_id: str, name: str, address: Optional[str], city: Optional[str]
    ) -> dict:
        """Insert a cinema row.

        Args:
            cinema_id: Unique identifier for the cinema.
            name: Display name of the cinema.
            address: Street address (optional).
            city: City where the cinema is located (optional).

        Returns:
            The inserted row as a dict.

        Raises:
            GatewayError: If a row with the given ``cinema_id`` already exists.
        """
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    f"""
                    INSERT INTO {self._table} (id, name, address, city)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, name, address, city
                    """,
                    cinema_id,
                    name,
                    address,
                    city,
                )
            except asyncpg.exceptions.UniqueViolationError:
                raise GatewayError(
                    f"A cinema with ID '{cinema_id}' already exists"
                ) from None
        return dict(row)

    async def find_by_id(self, cinema_id: str) -> Optional[dict]:
        """Find a cinema by its ID.

        Args:
            cinema_id: The unique identifier to look up.

        Returns:
            A dict representing the cinema row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT id, name, address, city FROM {self._table} WHERE id = $1",
                cinema_id,
            )
        return dict(row) if row is not None else None

    async def find_by_name_and_address(
        self, name: str, address: Optional[str]
    ) -> Optional[dict]:
        """Find a cinema by its exact name and address.

        Args:
            name: The cinema name.
            address: The cinema address (may be None).

        Returns:
            A dict representing the cinema row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT id, name, address, city FROM {self._table}
                WHERE name = $1 AND address IS NOT DISTINCT FROM $2
                """,
                name,
                address,
            )
        return dict(row) if row is not None else None

    async def exists_by_id(self, cinema_id: str) -> bool:
        """Check whether a cinema exists with the given ID.

        Args:
            cinema_id: The ID to check for.

        Returns:
            True if a row with that ID exists, False otherwise.
        """
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT EXISTS(SELECT 1 FROM {self._table} WHERE id = $1)",
                cinema_id,
            )
        return bool(result)
