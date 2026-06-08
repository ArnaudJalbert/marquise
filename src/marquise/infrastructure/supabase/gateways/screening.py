"""Supabase PostgreSQL implementation of ScreeningGateway."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import asyncpg

DEFAULT_SCHEMA = "marquise"

_COLUMNS = "id, movie_id, cinema_id, showtime, price"


class SupabaseScreeningGateway:
    """Concrete screening gateway that executes SQL against Supabase PostgreSQL.

    Args:
        pool: An open asyncpg connection pool.
        schema: The database schema where the screenings table lives
            (default ``marquise``).
    """

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        self._pool = pool
        self._table = f'"{schema}".screenings'

    async def save(
        self,
        screening_id: str,
        movie_id: str,
        cinema_id: str,
        showtime: datetime,
        price: float,
    ) -> dict:
        """Insert or upsert a screening row.

        Uses a unique constraint on (cinema_id, movie_id, showtime).

        Args:
            screening_id: Unique identifier.
            movie_id: The movie being screened.
            cinema_id: The cinema hosting the screening.
            showtime: The date and time of the screening.
            price: Ticket price.

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                WITH inserted AS (
                    INSERT INTO {self._table}
                        (id, movie_id, cinema_id, showtime, price)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (cinema_id, movie_id, showtime) DO NOTHING
                    RETURNING {_COLUMNS}, true AS __inserted
                ),
                updated AS (
                    UPDATE {self._table}
                    SET price = $5
                    WHERE cinema_id = $3 AND movie_id = $2
                        AND showtime = $4
                        AND NOT EXISTS (SELECT 1 FROM inserted)
                    RETURNING {_COLUMNS}, false AS __inserted
                )
                SELECT * FROM inserted
                UNION ALL
                SELECT * FROM updated
                """,
                screening_id,
                movie_id,
                cinema_id,
                showtime,
                price,
            )
        return dict(row)

    async def find_by_id(self, screening_id: str) -> Optional[dict]:
        """Find a screening by its ID.

        Args:
            screening_id: The unique identifier to look up.

        Returns:
            A dict representing the row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE id = $1",
                screening_id,
            )
        return dict(row) if row is not None else None

    async def find_by_cinema_and_date_range(
        self,
        cinema_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """Find screenings for a cinema within a date range.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).

        Returns:
            A list of dicts representing matching rows.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT {_COLUMNS} FROM {self._table}
                WHERE cinema_id = $1 AND showtime >= $2 AND showtime <= $3
                ORDER BY showtime
                """,
                cinema_id,
                start_date,
                end_date,
            )
        return [dict(r) for r in rows]
