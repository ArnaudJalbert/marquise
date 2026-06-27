"""Supabase PostgreSQL implementation of CinemaGateway."""

from __future__ import annotations

import asyncpg

from marquise.interface_adapters.repositories.protocols.cinema import GatewayError

DEFAULT_SCHEMA = "marquise"


_COLUMNS = "id, name, address, city, website"


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
        self,
        cinema_id: str,
        name: str,
        address: str | None,
        city: str | None,
        website: str | None = None,
    ) -> dict:
        """Insert or update (upsert) a cinema row.

        Args:
            cinema_id: Unique identifier for the cinema.
            name: Display name of the cinema.
            address: Street address (optional).
            city: City where the cinema is located (optional).
            website: Cinema website URL (optional).

        Returns:
            The inserted or updated row as a dict.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO {self._table} (id, name, address, city, website)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        address = EXCLUDED.address,
                        city = EXCLUDED.city,
                        website = EXCLUDED.website
                RETURNING {_COLUMNS}
                """,
                cinema_id,
                name,
                address,
                city,
                website,
            )
        return dict(row)

    async def find_by_id(self, cinema_id: str) -> dict | None:
        """Find a cinema by its ID.

        Args:
            cinema_id: The unique identifier to look up.

        Returns:
            A dict representing the cinema row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE id = $1",
                cinema_id,
            )
        return dict(row) if row is not None else None

    async def find_by_name_and_address(
        self, name: str, address: str | None
    ) -> dict | None:
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
                SELECT {_COLUMNS} FROM {self._table}
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

    async def delete(self, cinema_id: str) -> bool:
        """Delete a cinema by its ID.

        Args:
            cinema_id: The ID of the cinema to delete.

        Returns:
            True if a row was deleted, False otherwise.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table} WHERE id = $1",
                cinema_id,
            )
        return result != "DELETE 0"

    async def update(
        self,
        cinema_id: str,
        name: str,
        address: str | None,
        city: str | None,
        website: str | None = None,
    ) -> dict:
        """Update an existing cinema row.

        Args:
            cinema_id: The ID of the cinema to update.
            name: Updated display name.
            address: Updated street address (optional).
            city: Updated city (optional).
            website: Updated website URL (optional).

        Returns:
            The updated row as a dict.

        Raises:
            GatewayError: If no row with the given ``cinema_id`` exists.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE {self._table}
                SET name = $2, address = $3, city = $4, website = $5
                WHERE id = $1
                RETURNING {_COLUMNS}
                """,
                cinema_id,
                name,
                address,
                city,
                website,
            )
        if row is None:
            raise GatewayError(
                f"A cinema with ID '{cinema_id}' was not found"
            ) from None
        return dict(row)

    async def find_all(self, name_filter: str | None = None) -> list[dict]:
        """Retrieve all cinemas, optionally filtered by name.

        Args:
            name_filter: An optional substring to match against cinema names
                (case-insensitive). If None, all cinemas are returned.

        Returns:
            A list of dicts representing cinema rows.
        """
        async with self._pool.acquire() as conn:
            if name_filter:
                rows = await conn.fetch(
                    f"""
                    SELECT {_COLUMNS} FROM {self._table}
                    WHERE LOWER(name) LIKE LOWER($1)
                    ORDER BY name
                    """,
                    f"%{name_filter}%",
                )
            else:
                rows = await conn.fetch(
                    f"SELECT {_COLUMNS} FROM {self._table} ORDER BY name"
                )
        return [dict(r) for r in rows]
