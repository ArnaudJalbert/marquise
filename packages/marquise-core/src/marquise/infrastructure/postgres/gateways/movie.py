"""PostgreSQL implementation of MovieGateway."""

from __future__ import annotations

import asyncpg
from asyncpg.exceptions import UniqueViolationError

from marquise.interface_adapters.repositories.protocols.base import (
    GatewayError,
    GatewayPage,
)

DEFAULT_SCHEMA = "marquise"

_COLUMNS = (
    "id, title, release_year, directors, cast_members, duration_minutes, description,"
    " poster_url, trailer_url, genres, original_title, rating,"
    " origin_countries, tmdb_id, tmdb_rating, tmdb_vote_count"
)


class PostgresMovieGateway:
    """Concrete movie gateway that executes SQL against PostgreSQL.

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
        tmdb_id: str | None = None,
        tmdb_rating: float | None = None,
        tmdb_vote_count: int | None = None,
        *,
        update_existing: bool = True,
    ) -> dict:
        """Insert or upsert a movie row.

        Uses the unique index on the title, ignoring case.

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
            tmdb_id: Known TMDB identity, if any.
            tmdb_rating: TMDB user score, if fetched.
            tmdb_vote_count: TMDB vote count, if fetched.
            update_existing: Update matching titles, or return them unchanged.

        Returns:
            The inserted/updated row as a dict.

        Raises:
            GatewayError: On data-layer failure.
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                INSERT INTO {self._table}
                    (id, title, release_year, directors, cast_members,
                     duration_minutes, description, poster_url, trailer_url,
                     genres, original_title, rating, origin_countries, tmdb_id,
                     tmdb_rating, tmdb_vote_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT ((lower(title))) DO UPDATE
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
                                                    movies.origin_countries),
                        tmdb_id = COALESCE(EXCLUDED.tmdb_id, movies.tmdb_id),
                        tmdb_rating = COALESCE(EXCLUDED.tmdb_rating,
                                               movies.tmdb_rating),
                        tmdb_vote_count = COALESCE(EXCLUDED.tmdb_vote_count,
                                                   movies.tmdb_vote_count)
                WHERE $17 AND (movies.tmdb_id IS NULL OR EXCLUDED.tmdb_id IS NULL
                    OR movies.tmdb_id = EXCLUDED.tmdb_id)
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
                    tmdb_id,
                    tmdb_rating,
                    tmdb_vote_count,
                    update_existing,
                )
        except UniqueViolationError as exc:
            if (
                tmdb_id is not None
                and getattr(exc, "constraint_name", None) == "movies_tmdb_id_key"
            ):
                existing = await self.find_by_tmdb_id(tmdb_id)
                if existing is not None:
                    return existing
            raise
        if row is None and not update_existing:
            existing = (
                await self.find_by_tmdb_id(tmdb_id) if tmdb_id is not None else None
            )
            if existing is None:
                existing = await self.find_by_title(title)
            if existing is not None and (
                tmdb_id is None or existing["tmdb_id"] in {None, tmdb_id}
            ):
                return existing
        if row is None:
            raise GatewayError(f"Movie '{title}' already has a different TMDB id")
        return dict(row)

    async def find_by_tmdb_id(self, tmdb_id: str) -> dict | None:
        """Find a movie by its TMDB film id."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE tmdb_id = $1",
                tmdb_id,
            )
        return dict(row) if row is not None else None

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

    async def find_by_ids(self, movie_ids: list[str]) -> list[dict]:
        """Find movies by a list of IDs.

        Args:
            movie_ids: The unique identifiers to look up.

        Returns:
            A dict per matching row. IDs with no matching row are silently
            omitted — the returned list may be shorter than ``movie_ids``.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE id = ANY($1)",
                movie_ids,
            )
        return [dict(r) for r in rows]

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

    async def find_by_titles(self, titles: list[str]) -> list[dict]:
        """Find candidate movies containing any title term, case-insensitively.

        Args:
            titles: The title terms to search for.

        Returns:
            A dict per matching row. Terms with no match are silently omitted.
        """
        if not titles:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM {self._table} WHERE title ILIKE ANY($1)",
                [f"%{title}%" for title in titles],
            )
        return [dict(r) for r in rows]

    async def exists_by_id(self, movie_id: str) -> bool:
        """Check whether a movie exists with the given ID.

        Args:
            movie_id: The ID to check for.

        Returns:
            True if a row with that ID exists, False otherwise.
        """
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT EXISTS(SELECT 1 FROM {self._table} WHERE id = $1)",
                movie_id,
            )
        return bool(result)

    async def find_all(
        self,
        title_filter: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
        """Retrieve movies, optionally filtered by title and paginated.

        Args:
            title_filter: An optional substring to match against movie
                titles (case-insensitive). If None, all movies are returned.
            limit: Max number of rows to return. If None, all matching rows
                are returned unbounded (no ``LIMIT`` clause is applied).
            offset: Number of matching rows to skip before returning results.

        Returns:
            A ``GatewayPage`` with the matching rows (as dicts) and the total
            count of rows matching ``title_filter``, ignoring ``limit``/
            ``offset``.
        """
        where_clause = "WHERE LOWER(title) LIKE LOWER($1)" if title_filter else ""
        params: list = [f"%{title_filter}%"] if title_filter else []

        async with self._pool.acquire() as conn:
            if limit is None:
                rows = await conn.fetch(
                    f"""
                    SELECT {_COLUMNS} FROM {self._table}
                    {where_clause}
                    ORDER BY title
                    """,
                    *params,
                )
                return GatewayPage(rows=[dict(r) for r in rows], total=len(rows))

            limit_param = len(params) + 1
            offset_param = len(params) + 2
            rows = await conn.fetch(
                f"""
                SELECT {_COLUMNS}, COUNT(*) OVER() AS __total
                FROM {self._table}
                {where_clause}
                ORDER BY title
                LIMIT ${limit_param} OFFSET ${offset_param}
                """,
                *params,
                limit,
                offset,
            )
            if not rows:
                total = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {self._table} {where_clause}",
                    *params,
                )
                return GatewayPage(rows=[], total=total)

            total = rows[0]["__total"]
            result_rows = [dict(r) for r in rows]
            for row in result_rows:
                row.pop("__total")
        return GatewayPage(rows=result_rows, total=total)
