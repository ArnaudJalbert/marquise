"""Supabase reader for screening search display data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

from marquise.application.repositories import Page, ScreeningReader, ScreeningSummary

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


def _aware_utc(value: datetime) -> datetime:
    """Treat naive PostgreSQL timestamps as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class SupabaseScreeningReader(ScreeningReader):
    """Read screening search projections directly from Supabase."""

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        """Initialize with an open connection pool and schema."""
        self._pool = pool
        self._schema = schema

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
    ) -> Page[ScreeningSummary]:
        """Return screenings matching optional filters, paginated."""
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
                    ORDER BY s.showtime
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
                    ORDER BY s.showtime
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

        return Page(
            items=[
                ScreeningSummary(
                    id=row["id"],
                    movie_id=row["movie_id"],
                    movie_title=row["movie_title"],
                    cinema_id=row["cinema_id"],
                    cinema_name=row["cinema_name"],
                    showtime=_aware_utc(row["showtime"]),
                    ticket_url=row.get("ticket_url"),
                    room=row.get("room"),
                    language=row.get("language"),
                )
                for row in rows
            ],
            total=total,
        )
