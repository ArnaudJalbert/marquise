"""Supabase PostgreSQL implementation of MovieGateway."""

from __future__ import annotations

from datetime import date
from typing import Optional

import asyncpg

DEFAULT_SCHEMA = "marquise"

_COLUMNS = (
    "id, title, release_date, directors, cast_members, duration_minutes, description"
)


class SupabaseMovieGateway:
    """Concrete movie gateway that executes SQL against Supabase PostgreSQL.

    Args:
        pool: An open asyncpg connection pool.
        schema: The database schema where the movies table lives
            (default ``marquise``).
    """

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        self._pool = pool
        self._table = f'"{schema}".movies'

    async def save(
        self,
        movie_id: str,
        title: str,
        release_date: Optional[date],
        directors: Optional[str] = None,
        cast: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        description: Optional[str] = None,
    ) -> dict:
        """Insert or upsert a movie row.

        Uses a unique constraint on title.

        Args:
            movie_id: Unique identifier.
            title: Movie title.
            release_date: Release date (optional when unknown).
            directors: Comma-separated directors (None if unknown).
            cast: Comma-separated cast (None if unknown).
            duration_minutes: Duration in minutes.
            description: Movie description.

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO {self._table}
                    (id, title, release_date, directors, cast_members,
                     duration_minutes, description)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (title) DO UPDATE
                    SET release_date = COALESCE(EXCLUDED.release_date,
                                                movies.release_date),
                        directors = COALESCE(EXCLUDED.directors,
                                             movies.directors),
                        cast_members = COALESCE(EXCLUDED.cast_members,
                                                movies.cast_members),
                        duration_minutes = EXCLUDED.duration_minutes,
                        description = EXCLUDED.description
                RETURNING {_COLUMNS}
                """,
                movie_id,
                title,
                release_date,
                directors,
                cast,
                duration_minutes,
                description,
            )
        return dict(row)

    async def find_by_id(self, movie_id: str) -> Optional[dict]:
        """Find a movie by its ID.

        Args:
            movie_id: The unique identifier to look up.

        Returns:
            A dict representing the row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE id = $1",
                movie_id,
            )
        return dict(row) if row is not None else None

    async def find_by_title(self, title: str) -> Optional[dict]:
        """Find a movie by its exact title.

        Args:
            title: The movie title.

        Returns:
            A dict representing the row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE title = $1",
                title,
            )
        return dict(row) if row is not None else None
