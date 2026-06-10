"""Supabase PostgreSQL implementation of ScreeningGateway."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import asyncpg

DEFAULT_SCHEMA = "marquise"

_COLUMNS = "id, movie_id, cinema_id, showtime"
_MOVIE_COLUMNS = (
    "m.id AS movie__id, m.title AS movie__title,"
    " m.release_date AS movie__release_date,"
    " m.directors AS movie__directors,"
    " m.cast_members AS movie__cast_members,"
    " m.duration_minutes AS movie__duration_minutes,"
    " m.description AS movie__description"
)
_CINEMA_COLUMNS = (
    "c.id AS cinema__id, c.name AS cinema__name,"
    " c.address AS cinema__address, c.city AS cinema__city,"
    " c.website AS cinema__website"
)
_JOINED_COLUMNS = (
    f"s.id, s.movie_id, s.cinema_id, s.showtime, {_MOVIE_COLUMNS}, {_CINEMA_COLUMNS}"
)


def _naive_utc(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to naive UTC, or pass through if naive.

    Args:
        dt: The datetime to convert.

    Returns:
        A naive datetime in UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class SupabaseScreeningGateway:
    """Concrete screening gateway that executes SQL against Supabase PostgreSQL.

    Args:
        pool: An open asyncpg connection pool.
        schema: The database schema where the screenings table lives
            (default ``marquise``).
    """

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        self._pool = pool
        self._schema = schema
        self._table = f'"{schema}".screenings'

    async def save(
        self,
        screening_id: str,
        movie_id: str,
        cinema_id: str,
        showtime: datetime,
    ) -> dict:
        """Insert or upsert a screening row.

        Uses a unique constraint on (cinema_id, movie_id, showtime).

        Args:
            screening_id: Unique identifier.
            movie_id: The movie being screened.
            cinema_id: The cinema hosting the screening.
            showtime: The date and time of the screening.

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
                        (id, movie_id, cinema_id, showtime)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (cinema_id, movie_id, showtime) DO NOTHING
                    RETURNING {_COLUMNS}, true AS __inserted
                ),
                existing AS (
                    SELECT {_COLUMNS}, false AS __inserted
                    FROM {self._table}
                    WHERE cinema_id = $3 AND movie_id = $2
                        AND showtime = $4
                        AND NOT EXISTS (SELECT 1 FROM inserted)
                )
                SELECT * FROM inserted
                UNION ALL
                SELECT * FROM existing
                """,
                screening_id,
                movie_id,
                cinema_id,
                _naive_utc(showtime),
            )
        return dict(row)

    async def find_by_id(self, screening_id: str) -> Optional[dict]:
        """Find a screening by its ID.

        Args:
            screening_id: The unique identifier to look up.

        Returns:
            A dict representing the row with joined movie and cinema data,
            or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT {_JOINED_COLUMNS}
                FROM "{self._schema}".screenings s
                JOIN "{self._schema}".movies m ON s.movie_id = m.id
                JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                WHERE s.id = $1
                """,
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
            A list of dicts representing matching rows with joined
            movie and cinema data.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT {_JOINED_COLUMNS}
                FROM "{self._schema}".screenings s
                JOIN "{self._schema}".movies m ON s.movie_id = m.id
                JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                WHERE s.cinema_id = $1 AND s.showtime >= $2 AND s.showtime <= $3
                ORDER BY s.showtime
                """,
                cinema_id,
                _naive_utc(start_date),
                _naive_utc(end_date),
            )
        return [dict(r) for r in rows]
