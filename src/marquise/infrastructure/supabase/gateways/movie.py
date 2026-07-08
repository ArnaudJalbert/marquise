"""Supabase PostgreSQL implementation of MovieGateway."""

from __future__ import annotations

import asyncpg

DEFAULT_SCHEMA = "marquise"

_COLUMNS = (
    "id, title, release_year, directors, cast_members, duration_minutes, description,"
    " poster_url, trailer_url, genres, original_title, rating, origin_countries"
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
        release_year: int | None = None,
        directors: str | None = None,
        cast: str | None = None,
        duration_minutes: int | None = None,
        description: str | None = None,
        poster_url: str | None = None,
        trailer_url: str | None = None,
        genres: str | None = None,
        original_title: str | None = None,
        rating: str | None = None,
        origin_countries: str | None = None,
    ) -> dict:
        """Insert or upsert a movie row.

        Uses a unique constraint on title.

        Args:
            movie_id: Unique identifier.
            title: Movie title.
            release_year: Release year (optional when unknown).
            directors: Comma-separated directors (None if unknown).
            cast: Comma-separated cast (None if unknown).
            duration_minutes: Duration in minutes.
            description: Movie description.
            poster_url: URL to movie poster image (optional).
            trailer_url: URL to movie trailer (optional).
            genres: Comma-separated genres (optional).
            original_title: Original title in native language (optional).
            rating: Content rating (optional).
            origin_countries: Comma-separated origin countries (optional).

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO {self._table}
                    (id, title, release_year, directors, cast_members,
                     duration_minutes, description, poster_url, trailer_url,
                     genres, original_title, rating, origin_countries)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (title) DO UPDATE
                    SET release_year = COALESCE(EXCLUDED.release_year,
                                                movies.release_year),
                        directors = COALESCE(EXCLUDED.directors,
                                             movies.directors),
                        cast_members = COALESCE(EXCLUDED.cast_members,
                                                movies.cast_members),
                        duration_minutes = COALESCE(EXCLUDED.duration_minutes,
                                                    movies.duration_minutes),
                        description = COALESCE(EXCLUDED.description,
                                               movies.description),
                        poster_url = COALESCE(EXCLUDED.poster_url,
                                              movies.poster_url),
                        trailer_url = COALESCE(EXCLUDED.trailer_url,
                                               movies.trailer_url),
                        genres = COALESCE(EXCLUDED.genres,
                                          movies.genres),
                        original_title = COALESCE(EXCLUDED.original_title,
                                                  movies.original_title),
                        rating = COALESCE(EXCLUDED.rating,
                                          movies.rating),
                        origin_countries = COALESCE(EXCLUDED.origin_countries,
                                                    movies.origin_countries)
                RETURNING {_COLUMNS}
                """,
                movie_id,
                title,
                release_year,
                directors,
                cast,
                duration_minutes,
                description,
                poster_url,
                trailer_url,
                genres,
                original_title,
                rating,
                origin_countries,
            )
        return dict(row)

    async def find_by_id(self, movie_id: str) -> dict | None:
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

    async def find_by_title(self, title: str) -> dict | None:
        """Find a movie by title, case-insensitively.

        Args:
            title: The movie title.

        Returns:
            A dict representing the row, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE LOWER(title) = LOWER($1)",
                title,
            )
        return dict(row) if row is not None else None
