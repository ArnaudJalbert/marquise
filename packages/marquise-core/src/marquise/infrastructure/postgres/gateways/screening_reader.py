"""PostgreSQL gateway for screening display projections."""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from marquise.interface_adapters.repositories.protocols.base import GatewayPage

DEFAULT_SCHEMA = "marquise"
_COLUMNS = (
    "s.id, s.movie_id, s.cinema_id, s.showtime,"
    " s.ticket_url, s.room, s.language,"
    " m.title AS movie_title, c.name AS cinema_name"
)


def _naive_utc(value: datetime) -> datetime:
    """Convert an aware datetime to naive UTC for PostgreSQL."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


class PostgresScreeningReadGateway:
    """Read plain screening display rows from PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        """Initialize with an open connection pool and schema."""
        self._pool = pool
        self._schema = schema

    async def find_by_id(self, screening_id: str) -> dict | None:
        """Return one display row for an exact ID, or None if missing."""
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                f"""
                SELECT {_COLUMNS}
                FROM "{self._schema}".screenings s
                JOIN "{self._schema}".movies m ON s.movie_id = m.id
                JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                WHERE s.id = $1
                """,
                screening_id,
            )
        return dict(row) if row is not None else None

    async def search(
        self,
        movie_id: str | None = None,
        movie_title: str | None = None,
        cinema_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        language: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
        """Return display rows matching optional filters and their total count."""
        conditions: list[str] = []
        params: list[str | datetime] = []

        def add_condition(expression: str, value: str | datetime) -> None:
            params.append(value)
            conditions.append(f"{expression} ${len(params)}")

        if movie_id is not None:
            add_condition("s.movie_id =", movie_id)
        if movie_title is not None:
            add_condition("m.title ILIKE", f"%{movie_title}%")
        if cinema_id is not None:
            add_condition("s.cinema_id =", cinema_id)
        if start_date is not None:
            add_condition("s.showtime >=", _naive_utc(start_date))
        if end_date is not None:
            add_condition("s.showtime <=", _naive_utc(end_date))
        if language is not None:
            add_condition("s.language =", language)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        async with self._pool.acquire() as connection:
            if limit is None:
                rows = await connection.fetch(
                    f"""
                    SELECT {_COLUMNS}
                    FROM "{self._schema}".screenings s
                    JOIN "{self._schema}".movies m ON s.movie_id = m.id
                    JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                    {where}
                    ORDER BY s.showtime, s.id
                    """,
                    *params,
                )
                total = len(rows)
            else:
                rows = await connection.fetch(
                    f"""
                    SELECT {_COLUMNS}, COUNT(*) OVER() AS __total
                    FROM "{self._schema}".screenings s
                    JOIN "{self._schema}".movies m ON s.movie_id = m.id
                    JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                    {where}
                    ORDER BY s.showtime, s.id
                    LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
                    """,
                    *params,
                    limit,
                    offset,
                )
                total = (
                    rows[0]["__total"]
                    if rows
                    else await connection.fetchval(
                        f"""
                        SELECT COUNT(*)
                        FROM "{self._schema}".screenings s
                        JOIN "{self._schema}".movies m ON s.movie_id = m.id
                        {where}
                        """,
                        *params,
                    )
                )

        result_rows = [dict(row) for row in rows]
        for row in result_rows:
            row.pop("__total", None)
        return GatewayPage(rows=result_rows, total=total)
