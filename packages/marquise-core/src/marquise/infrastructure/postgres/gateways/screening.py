"""PostgreSQL implementation of ScreeningGateway."""

from __future__ import annotations

from datetime import datetime

import asyncpg

from marquise.infrastructure.postgres.timestamps import to_naive_utc
from marquise.interface_adapters.repositories.protocols.base import (
    GatewayError,
    GatewayPage,
)
from marquise.interface_adapters.repositories.protocols.screening import (
    SaveOutcome,
    ScreeningExternalIdConflictGatewayError,
    ScreeningWriteConflictGatewayError,
)

_COLUMNS = (
    "id, movie_id, cinema_id, showtime, external_id, source_name, "
    "ticket_url, room, language"
)
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
    " m.origin_countries AS movie__origin_countries,"
    " m.tmdb_id AS movie__tmdb_id, m.tmdb_rating AS movie__tmdb_rating,"
    " m.tmdb_vote_count AS movie__tmdb_vote_count"
)
_CINEMA_COLUMNS = (
    "c.id AS cinema__id, c.name AS cinema__name,"
    " c.address AS cinema__address, c.city AS cinema__city,"
    " c.website AS cinema__website"
)
_SCREENING_COLUMNS = (
    "s.id, s.movie_id, s.cinema_id, s.showtime,"
    " s.external_id, s.source_name, s.ticket_url, s.room, s.language"
)
_JOINED_COLUMNS = f"{_SCREENING_COLUMNS}, {_MOVIE_COLUMNS}, {_CINEMA_COLUMNS}"
_PLAIN_MOVIE_COLUMNS = (
    "m.id, m.title, m.release_year, m.directors, m.cast_members,"
    " m.duration_minutes, m.description, m.poster_url, m.trailer_url,"
    " m.genres, m.original_title, m.rating, m.origin_countries,"
    " m.tmdb_id, m.tmdb_rating, m.tmdb_vote_count"
)


def _to_stored_row(data: dict) -> dict:
    """Copy screening persistence data with its showtime in stored form."""
    return {**data, "showtime": to_naive_utc(data["showtime"])}


class PostgresScreeningGateway:
    """Concrete screening gateway that executes SQL against PostgreSQL.

    Args:
        pool: An open asyncpg connection pool.
        schema: The database schema where the screenings table lives.
    """

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
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
        source_name: str | None = None,
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
            ScreeningExternalIdConflictGatewayError: If the external ID
                belongs to another screening.
            GatewayError: If the upsert returns no row.
            asyncpg.PostgresError: On other database failures.
        """
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    f"""
                    INSERT INTO {self._table}
                        (id, movie_id, cinema_id, showtime,
                         external_id, source_name, ticket_url, room, language)
                    VALUES ($1, $2, $3, $4, NULLIF($5, ''), $6, $7, $8, $9)
                    ON CONFLICT (cinema_id, movie_id, showtime) DO NOTHING
                    RETURNING {_COLUMNS}
                    """,
                    screening_id,
                    movie_id,
                    cinema_id,
                    to_naive_utc(showtime),
                    external_id,
                    source_name,
                    ticket_url,
                    room,
                    language,
                )
            except asyncpg.exceptions.UniqueViolationError as exc:
                if exc.as_dict().get("constraint_name") != "screenings_external_id_key":
                    raise
                raise ScreeningExternalIdConflictGatewayError(
                    f"external_id={external_id!r} belongs to another screening"
                ) from exc
            inserted = row is not None
            if row is None:
                # A conflict may wait for a row absent from INSERT's snapshot.
                row = await conn.fetchrow(
                    f"SELECT {_COLUMNS} FROM {self._table} "
                    "WHERE cinema_id = $1 AND movie_id = $2 AND showtime = $3",
                    cinema_id,
                    movie_id,
                    to_naive_utc(showtime),
                )
        if row is None:
            raise GatewayError("Screening disappeared after the identity conflict")
        return SaveOutcome(row=dict(row), inserted=inserted)

    async def read_import_candidates(
        self,
        cinema_id: str,
        movie_id: str,
        showtime: datetime,
        external_id: str | None,
    ) -> list[dict]:
        """Read every row matching the native key or target identity."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_JOINED_COLUMNS} FROM {self._table} s "
                f'JOIN "{self._schema}".movies m ON s.movie_id = m.id '
                f'JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id '
                "WHERE s.cinema_id = $1 AND ("
                "(s.movie_id = $2 AND s.showtime = $3) "
                "OR (NULLIF($4::text, '') IS NOT NULL AND s.external_id = $4)) "
                "ORDER BY s.id",
                cinema_id,
                movie_id,
                to_naive_utc(showtime),
                external_id,
            )
        return [dict(row) for row in rows]

    async def commit_import(
        self, proposed: dict, *, incoming: dict, expected: tuple[dict, ...]
    ) -> dict:
        """Lock checked rows, compare full snapshots, and persist atomically.

        Uniqueness protects absent target/native keys against concurrent arrivals.
        The fresh read after locking detects rows committed during lock waits.
        No source ownership or calendar eligibility rule is evaluated here.
        """
        stored_expected = tuple(_to_stored_row(row) for row in expected)
        async with self._pool.acquire() as conn:
            try:
                async with conn.transaction(isolation="read_committed"):
                    await self._check_import_snapshot(
                        conn, _to_stored_row(incoming), stored_expected
                    )
                    return await self._persist_import(
                        conn,
                        _to_stored_row(proposed),
                        replacing=any(row["id"] == proposed["id"] for row in expected),
                    )
            except (asyncpg.UniqueViolationError, asyncpg.DeadlockDetectedError) as exc:
                raise ScreeningWriteConflictGatewayError(
                    "Concurrent Screening identity or native-key conflict"
                ) from exc

    async def _check_import_snapshot(
        self, conn: asyncpg.Connection, incoming: dict, expected: tuple[dict, ...]
    ) -> None:
        """Lock all checked rows and compare a fresh snapshot after any lock wait."""
        query = (
            f"SELECT {_COLUMNS} FROM {self._table} "
            "WHERE id = ANY($5::text[]) OR (cinema_id = $1 AND ("
            "(movie_id = $2 AND showtime = $3) "
            "OR (NULLIF($4::text, '') IS NOT NULL AND external_id = $4))) "
            "ORDER BY id FOR UPDATE"
        )
        checked = {row["id"]: row for row in expected}
        arguments = (
            incoming["cinema_id"],
            incoming["movie_id"],
            incoming["showtime"],
            incoming["external_id"],
            list(checked),
        )

        await conn.fetch(query, *arguments)
        current = await conn.fetch(query, *arguments)
        if {row["id"]: dict(row) for row in current} != checked:
            raise ScreeningWriteConflictGatewayError("Screening state changed")

    async def _persist_import(
        self, conn: asyncpg.Connection, proposed: dict, *, replacing: bool
    ) -> dict:
        """Insert or replace the complete row and load its joined persistence data."""
        columns = _COLUMNS.split(", ")
        values = tuple(proposed[column] for column in columns)
        if replacing:
            assignments = ", ".join(
                f"{column} = ${index}"
                for index, column in enumerate(columns[1:], start=2)
            )
            await conn.execute(
                f"UPDATE {self._table} SET {assignments} WHERE id = $1",
                *values,
            )
        else:
            placeholders = ", ".join(f"${i}" for i in range(1, len(columns) + 1))
            await conn.execute(
                f"INSERT INTO {self._table} ({_COLUMNS}) VALUES ({placeholders})",
                *values,
            )
        row = await conn.fetchrow(
            f"SELECT {_JOINED_COLUMNS} FROM {self._table} s "
            f'JOIN "{self._schema}".movies m ON s.movie_id = m.id '
            f'JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id '
            "WHERE s.id = $1",
            proposed["id"],
        )
        if row is None:
            raise GatewayError("Persisted Screening has missing parents")
        return dict(row)

    async def replace(
        self,
        screening_id: str,
        movie_id: str,
        cinema_id: str,
        showtime: datetime,
        external_id: str | None = None,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
        *,
        fields: frozenset[str],
    ) -> dict | None:
        """Replace specified fields of a screening identified by ID.

        Args:
            screening_id: The unique identifier of the row to replace.
            movie_id: Replacement movie ID.
            cinema_id: Replacement cinema ID.
            showtime: Replacement screening time.
            external_id: Replacement source-native key (optional).
            ticket_url: Replacement ticket URL (optional).
            room: Replacement room name (optional).
            language: Replacement language (optional).
            fields: Columns explicitly supplied by the caller; an empty set
                reads the current row without writing.

        Returns:
            The updated row with joined parents, or None if no matching row exists.

        Raises:
            ValueError: If the mask contains an unsupported column.
            ScreeningExternalIdConflictGatewayError: If the external ID belongs
                to another screening.
            GatewayError: If the screening identity collides with another row.
            asyncpg.PostgresError: On other database failures.
        """
        values: dict[str, str | datetime | None] = {
            "movie_id": movie_id,
            "cinema_id": cinema_id,
            "showtime": to_naive_utc(showtime),
            "external_id": external_id,
            "ticket_url": ticket_url,
            "room": room,
            "language": language,
        }
        if not fields.issubset(values):
            raise ValueError("Unsupported screening replacement field")
        if fields == frozenset():
            return await self.find_by_id(screening_id)
        # Only fixed, whitelisted identifiers enter SQL; values are always bound.
        columns = [name for name in values if name in fields]
        assignments = ", ".join(
            f"{name} = ${index}" for index, name in enumerate(columns, start=2)
        )
        ownership_changes = [
            f"{name} IS DISTINCT FROM ${columns.index(name) + 2}"
            for name in ("cinema_id", "external_id")
            if name in fields
        ]
        if ownership_changes:
            assignments += (
                ", source_name = CASE WHEN "
                + " OR ".join(ownership_changes)
                + " THEN NULL ELSE source_name END"
            )
        async with (
            self._pool.acquire() as conn,
            conn.transaction(isolation="read_committed"),
        ):
            try:
                row = await conn.fetchrow(
                    f"""
                    WITH updated AS (
                        UPDATE {self._table}
                        SET {assignments}
                        WHERE id = $1
                        RETURNING {_COLUMNS}
                    )
                    SELECT {_JOINED_COLUMNS}
                    FROM updated s
                    LEFT JOIN "{self._schema}".movies m ON s.movie_id = m.id
                    LEFT JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                    """,
                    screening_id,
                    *(values[name] for name in columns),
                )
                if row is not None and (
                    row["movie__id"] is None or row["cinema__id"] is None
                ):
                    # UPDATE can wait for a reparenting transaction whose newly
                    # inserted parent is invisible to the CTE's initial snapshot.
                    # Keep the updated screening locked and retry the join with
                    # a fresh snapshot before reporting a missing screening.
                    row = await conn.fetchrow(
                        f"""
                        SELECT {_JOINED_COLUMNS}
                        FROM {self._table} s
                        JOIN "{self._schema}".movies m ON s.movie_id = m.id
                        JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                        WHERE s.id = $1
                        """,
                        screening_id,
                    )
            except asyncpg.exceptions.UniqueViolationError as exc:
                constraint = exc.as_dict().get("constraint_name")
                if constraint == "screenings_external_id_key":
                    raise ScreeningExternalIdConflictGatewayError(
                        f"external_id={external_id!r} belongs to another screening"
                    ) from exc
                if constraint != "screenings_cinema_id_movie_id_showtime_key":
                    raise
                raise GatewayError(
                    "A screening already exists for the replacement identity"
                ) from exc
        return dict(row) if row is not None else None

    async def delete(self, screening_id: str) -> bool:
        """Delete a screening and atomically remove its movie if now orphaned.

        Args:
            screening_id: The unique identifier of the row to delete.

        Returns:
            True if a row was deleted, False if no row has the given ID.
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction(isolation="read_committed"):
                row = await conn.fetchrow(
                    f"DELETE FROM {self._table} WHERE id = $1 RETURNING movie_id",
                    screening_id,
                )
                if row is None:
                    return False
                movie_id = row["movie_id"]
                # DELETE locks the screening first, so concurrent reparenting
                # cannot change which movie is cleaned up. The parent lock
                # blocks FK KEY SHARE locks from new screenings. Use a separate
                # statement after acquiring it for a fresh READ COMMITTED view.
                await conn.fetchrow(
                    f'SELECT id FROM "{self._schema}".movies WHERE id = $1 FOR UPDATE',
                    movie_id,
                )
                await conn.execute(
                    f"""
                    DELETE FROM "{self._schema}".movies m
                    WHERE m.id = $1 AND NOT EXISTS (
                        SELECT 1 FROM {self._table} s WHERE s.movie_id = m.id
                    )
                    """,
                    movie_id,
                )
        return True

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

    async def find_distinct_movies_by_cinema(
        self,
        cinema_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> GatewayPage:
        """Find distinct movies with a screening at a cinema in a date range.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the showtime range (inclusive).
            end_date: End of the showtime range (inclusive).
            limit: Max number of movies to return. If None, all matching
                movies are returned unbounded (no ``LIMIT`` clause is
                applied).
            offset: Number of matching movies to skip before returning
                results.

        Returns:
            A ``GatewayPage`` with the matching movie rows (plain movie
            columns, not prefixed) and the total count of distinct movies
            matching the cinema and date range, ignoring ``limit``/``offset``.
        """
        params = (cinema_id, to_naive_utc(start_date), to_naive_utc(end_date))
        where_clause = (
            "WHERE s.cinema_id = $1 AND s.showtime >= $2 AND s.showtime <= $3"
        )

        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                f"""
                SELECT COUNT(DISTINCT s.movie_id)
                FROM "{self._schema}".screenings s
                {where_clause}
                """,
                *params,
            )

            distinct_movies_query = f"""
                SELECT DISTINCT ON (m.id) {_PLAIN_MOVIE_COLUMNS}
                FROM "{self._schema}".screenings s
                JOIN "{self._schema}".movies m ON s.movie_id = m.id
                {where_clause}
                ORDER BY m.id
            """
            if limit is None:
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM ({distinct_movies_query}) AS distinct_movies
                    ORDER BY title
                    """,
                    *params,
                )
            else:
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM ({distinct_movies_query}) AS distinct_movies
                    ORDER BY title
                    LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
                    """,
                    *params,
                    limit,
                    offset,
                )
        return GatewayPage(rows=[dict(r) for r in rows], total=total)
