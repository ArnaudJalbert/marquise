"""Supabase PostgreSQL implementation of ScreeningGateway."""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from marquise.interface_adapters.repositories.protocols.base import (
    GatewayError,
    GatewayPage,
)
from marquise.interface_adapters.repositories.protocols.screening import SaveOutcome

DEFAULT_SCHEMA = "marquise"

_COLUMNS = "id, movie_id, cinema_id, showtime, external_id, ticket_url, room, language"
_MOVIE_COLUMNS = (
    "m.id AS movie__id, m.title AS movie__title,"
    " m.release_year AS movie__release_year,"
    " m.directors AS movie__directors,"
    " m.cast_members AS movie__cast_members,"
    " m.duration_minutes AS movie__duration_minutes,"
    " m.description AS movie__description,"
    " m.poster_url AS movie__poster_url,"
    " m.trailer_url AS movie__trailer_url,"
    " m.genres AS movie__genres,"
    " m.original_title AS movie__original_title,"
    " m.rating AS movie__rating,"
    " m.origin_countries AS movie__origin_countries"
)
_CINEMA_COLUMNS = (
    "c.id AS cinema__id, c.name AS cinema__name,"
    " c.address AS cinema__address, c.city AS cinema__city,"
    " c.website AS cinema__website"
)
_SCREENING_COLUMNS = (
    "s.id, s.movie_id, s.cinema_id, s.showtime,"
    " s.external_id, s.ticket_url, s.room, s.language"
)
_JOINED_COLUMNS = f"{_SCREENING_COLUMNS}, {_MOVIE_COLUMNS}, {_CINEMA_COLUMNS}"


def _naive_utc(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to naive UTC, or pass through if naive.

    Args:
        dt: The datetime to convert.

    Returns:
        A naive datetime in UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
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
        external_id: str | None = None,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
    ) -> SaveOutcome:
        """Insert or upsert a screening row.

        Uses a unique constraint on (cinema_id, movie_id, showtime).

        Args:
            screening_id: Unique identifier.
            movie_id: The movie being screened.
            cinema_id: The cinema hosting the screening.
            showtime: The date and time of the screening.
            external_id: Source-native deduplication key (optional).
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).

        Returns:
            A ``SaveOutcome`` carrying the row and whether it was newly inserted.

        Raises:
            GatewayError: On data-layer failure, including when
                ``external_id`` collides with a row that has a different
                (cinema_id, movie_id, showtime).
        """
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    f"""
                    WITH inserted AS (
                        INSERT INTO {self._table}
                            (id, movie_id, cinema_id, showtime,
                             external_id, ticket_url, room, language)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
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
                    external_id,
                    ticket_url,
                    room,
                    language,
                )
            except asyncpg.exceptions.UniqueViolationError as exc:
                raise GatewayError(
                    f"A screening with external_id={external_id!r} already "
                    "exists for a different (cinema_id, movie_id, showtime)"
                ) from exc
        if row is None:
            raise GatewayError(
                f"Screening upsert returned no row for "
                f"(cinema_id={cinema_id!r}, movie_id={movie_id!r}, "
                f"showtime={showtime}). This usually means a duplicate "
                f"(cinema_id, movie_id, showtime) was upserted concurrently — "
                f"deduplicate rows before calling save()."
            )
        data = dict(row)
        inserted = bool(data.pop("__inserted"))
        return SaveOutcome(row=data, inserted=inserted)

    async def update(
        self,
        cinema_id: str,
        movie_id: str,
        showtime: datetime,
        external_id: str | None = None,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
    ) -> dict | None:
        """Update optional fields on an existing screening.

        Matches by the unique constraint (cinema_id, movie_id, showtime).
        Only non-None values are written; existing values are preserved
        when the argument is None.

        Args:
            cinema_id: The cinema hosting the screening.
            movie_id: The movie being screened.
            showtime: The date and time of the screening.
            external_id: Source-native deduplication key (optional).
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).

        Returns:
            The updated row as a dict, or None if no matching row exists.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE {self._table}
                SET
                    external_id = COALESCE($4, external_id),
                    ticket_url = COALESCE($5, ticket_url),
                    room = COALESCE($6, room),
                    language = COALESCE($7, language)
                WHERE cinema_id = $1 AND movie_id = $2 AND showtime = $3
                RETURNING {_COLUMNS}
                """,
                cinema_id,
                movie_id,
                _naive_utc(showtime),
                external_id,
                ticket_url,
                room,
                language,
            )
        return dict(row) if row is not None else None

    async def find_by_id(self, screening_id: str) -> dict | None:
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
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
        """Find screenings for a cinema within a date range, paginated.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).
            limit: Max number of rows to return. If None, all matching rows
                are returned unbounded (no ``LIMIT`` clause is applied).
            offset: Number of matching rows to skip before returning results.

        Returns:
            A ``GatewayPage`` with the matching rows (joined with movie and
            cinema data) and the total count of rows matching the cinema
            and date range, ignoring ``limit``/``offset``.
        """
        params = (cinema_id, _naive_utc(start_date), _naive_utc(end_date))
        where_clause = (
            "WHERE s.cinema_id = $1 AND s.showtime >= $2 AND s.showtime <= $3"
        )

        async with self._pool.acquire() as conn:
            if limit is None:
                rows = await conn.fetch(
                    f"""
                    SELECT {_JOINED_COLUMNS}
                    FROM "{self._schema}".screenings s
                    JOIN "{self._schema}".movies m ON s.movie_id = m.id
                    JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                    {where_clause}
                    ORDER BY s.showtime
                    """,
                    *params,
                )
                return GatewayPage(rows=[dict(r) for r in rows], total=len(rows))

            # COUNT(*) OVER() rides along with the paginated SELECT so the
            # common case (a non-empty page) costs one round trip. It can't
            # report a total when the page itself is empty (e.g. offset past
            # the end of the result set), since there is no row to read it
            # off — that case falls back to a separate, cheap COUNT(*)
            # against the screenings table alone (no joins needed).
            rows = await conn.fetch(
                f"""
                SELECT {_JOINED_COLUMNS}, COUNT(*) OVER() AS __total
                FROM "{self._schema}".screenings s
                JOIN "{self._schema}".movies m ON s.movie_id = m.id
                JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                {where_clause}
                ORDER BY s.showtime
                LIMIT $4 OFFSET $5
                """,
                *params,
                limit,
                offset,
            )
            if not rows:
                total = await conn.fetchval(
                    f"""
                    SELECT COUNT(*) FROM "{self._schema}".screenings s
                    {where_clause}
                    """,
                    *params,
                )
                return GatewayPage(rows=[], total=total)

            total = rows[0]["__total"]
            result_rows = [dict(r) for r in rows]
            for row in result_rows:
                row.pop("__total")
        return GatewayPage(rows=result_rows, total=total)
