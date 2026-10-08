"""Supabase PostgreSQL implementation of ScreeningGateway."""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from marquise.infrastructure.supabase.connection_pool import ConnectionPool
from marquise.interface_adapters.repositories.protocols.base import (
    GatewayError,
    GatewayPage,
)
from marquise.interface_adapters.repositories.protocols.screening import (
    SaveOutcome,
    ScreeningExternalIdConflictGatewayError,
    ScreeningRescheduleConflictGatewayError,
)

DEFAULT_SCHEMA = "marquise"

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
    " m.origin_countries AS movie__origin_countries"
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
    " m.genres, m.original_title, m.rating, m.origin_countries"
)


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

    def __init__(self, pool: ConnectionPool, schema: str = DEFAULT_SCHEMA) -> None:
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
                    _naive_utc(showtime),
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
                    _naive_utc(showtime),
                )
        if row is None:
            raise GatewayError("Screening disappeared after the identity conflict")
        return SaveOutcome(row=dict(row), inserted=inserted)

    async def reschedule(
        self,
        cinema_id: str,
        movie_id: str,
        external_id: str,
        source_name: str,
        showtime: datetime,
        local_day_start: datetime,
        local_day_end: datetime,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
    ) -> dict | None:
        """Move one same-day source-owned screening without changing its ID."""
        if not external_id or not source_name:
            return None
        async with self._pool.acquire() as conn:
            async with conn.transaction(isolation="read_committed"):
                owners = await conn.fetch(
                    f"SELECT {_COLUMNS} FROM {self._table} "
                    "WHERE cinema_id = $1 AND external_id = $2 ORDER BY id FOR UPDATE",
                    cinema_id,
                    external_id,
                )
                if not owners:
                    return None
                if len(owners) != 1:
                    raise ScreeningExternalIdConflictGatewayError(
                        f"Ambiguous ownership: {len(owners)} Screenings claim "
                        f"cinema_id={cinema_id!r} external_id={external_id!r}"
                    )
                owner = owners[0]
                try:
                    row = await conn.fetchrow(
                        f"""
                        WITH updated AS (
                            UPDATE {self._table}
                            SET showtime = $7,
                                ticket_url = COALESCE($8, ticket_url),
                                room = COALESCE($9, room),
                                language = COALESCE($10, language)
                            WHERE id = $1 AND movie_id = $2
                                AND external_id = $3 AND source_name = $4
                                AND showtime >= $5 AND showtime < $6
                                AND $7 >= $5 AND $7 < $6
                            RETURNING {_COLUMNS}
                        )
                        SELECT {_JOINED_COLUMNS}
                        FROM updated s
                        JOIN "{self._schema}".movies m ON s.movie_id = m.id
                        JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                        """,
                        owner["id"],
                        movie_id,
                        external_id,
                        source_name,
                        _naive_utc(local_day_start),
                        _naive_utc(local_day_end),
                        _naive_utc(showtime),
                        ticket_url,
                        room,
                        language,
                    )
                    if row is None:
                        raise ScreeningExternalIdConflictGatewayError(
                            f"Reschedule refused: owner_id={owner['id']!r}, "
                            f"movie_id={owner['movie_id']!r} (incoming={movie_id!r}), "
                            f"showtime={owner['showtime']}, "
                            f"allowed_window=[{local_day_start}, {local_day_end}), "
                            f"source provenance={owner['source_name']!r} "
                            f"(incoming={source_name!r})"
                        )
                except asyncpg.exceptions.UniqueViolationError as exc:
                    if exc.as_dict().get("constraint_name") == (
                        "screenings_cinema_id_movie_id_showtime_key"
                    ):
                        raise ScreeningRescheduleConflictGatewayError(
                            "A screening already exists for the rescheduled identity"
                        ) from exc
                    raise
        return dict(row) if row is not None else None

    async def update(
        self,
        cinema_id: str,
        movie_id: str,
        showtime: datetime,
        external_id: str | None = None,
        source_name: str | None = None,
        ticket_url: str | None = None,
        room: str | None = None,
        language: str | None = None,
    ) -> dict | None:
        """Update optional fields on an existing screening.

        Matches by the unique constraint (cinema_id, movie_id, showtime).
        None or blank native IDs preserve the existing key and its provenance.
        A provided key requires source evidence to acquire or transfer provenance.
        Other optional values are written only when non-None.

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

        Raises:
            ScreeningExternalIdConflictGatewayError: If the external ID
                belongs to another screening.
            asyncpg.PostgresError: On other database failures.
        """
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    f"""
                    UPDATE {self._table}
                    SET
                        external_id = COALESCE(NULLIF($4, ''), external_id),
                        source_name = CASE
                            WHEN NULLIF($4, '') IS NULL THEN source_name
                            WHEN $5::text IS NOT NULL THEN $5
                            WHEN $4 IS DISTINCT FROM external_id THEN NULL
                            ELSE source_name
                        END,
                        ticket_url = COALESCE($6, ticket_url),
                        room = COALESCE($7, room),
                        language = COALESCE($8, language)
                    WHERE cinema_id = $1 AND movie_id = $2 AND showtime = $3
                        AND (
                            $5::text IS NULL OR source_name IS NULL OR source_name = $5
                        )
                    RETURNING {_COLUMNS}
                    """,
                    cinema_id,
                    movie_id,
                    _naive_utc(showtime),
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
            if row is None and source_name is not None:
                existing = await conn.fetchrow(
                    f"SELECT id, source_name FROM {self._table} "
                    "WHERE cinema_id = $1 AND movie_id = $2 AND showtime = $3",
                    cinema_id,
                    movie_id,
                    _naive_utc(showtime),
                )
                if existing is not None:
                    raise ScreeningExternalIdConflictGatewayError(
                        f"Metadata update refused: owner_id={existing['id']!r}, "
                        f"source provenance={existing['source_name']!r} "
                        f"(incoming={source_name!r})"
                    )
        return dict(row) if row is not None else None

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
            "showtime": _naive_utc(showtime),
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

    async def delete(self, screening_id: str) -> None:
        """Delete a screening and atomically remove its movie if now orphaned.

        Args:
            screening_id: The unique identifier of the row to delete.

        Raises:
            GatewayError: If no row has the given ID.
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction(isolation="read_committed"):
                row = await conn.fetchrow(
                    f"DELETE FROM {self._table} WHERE id = $1 RETURNING movie_id",
                    screening_id,
                )
                if row is None:
                    raise GatewayError(
                        f"A screening with ID '{screening_id}' was not found"
                    )
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
        """Find screenings matching any combination of filters, paginated.

        Args:
            movie_id: Filter by exact movie ID.
            movie_title: Filter by movie title substring (case-insensitive).
            cinema_id: Filter by exact cinema ID.
            start_date: Start of the showtime range (inclusive).
            end_date: End of the showtime range (inclusive).
            language: Filter by exact language/subtitle version.
            limit: Max number of rows to return. If None, all matching rows
                are returned unbounded (no ``LIMIT`` clause is applied).
            offset: Number of matching rows to skip before returning results.

        Returns:
            A ``GatewayPage`` with the matching rows (joined with movie and
            cinema data) and the total count of rows matching the filters,
            ignoring ``limit``/``offset``.
        """
        conditions: list[str] = []
        params: list[object] = []

        def _add(expr: str, value: object) -> None:
            params.append(value)
            conditions.append(f"{expr} ${len(params)}")

        if movie_id is not None:
            _add("s.movie_id =", movie_id)
        if movie_title is not None:
            _add("m.title ILIKE", f"%{movie_title}%")
        if cinema_id is not None:
            _add("s.cinema_id =", cinema_id)
        if start_date is not None:
            _add("s.showtime >=", _naive_utc(start_date))
        if end_date is not None:
            _add("s.showtime <=", _naive_utc(end_date))
        if language is not None:
            _add("s.language =", language)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self._pool.acquire() as conn:
            if limit is None:
                rows = await conn.fetch(
                    f"""
                    SELECT {_JOINED_COLUMNS}
                    FROM "{self._schema}".screenings s
                    JOIN "{self._schema}".movies m ON s.movie_id = m.id
                    JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                    {where_clause}
                    ORDER BY s.showtime, s.id
                    """,
                    *params,
                )
                return GatewayPage(rows=[dict(r) for r in rows], total=len(rows))

            limit_param = f"${len(params) + 1}"
            offset_param = f"${len(params) + 2}"
            rows = await conn.fetch(
                f"""
                SELECT {_JOINED_COLUMNS}, COUNT(*) OVER() AS __total
                FROM "{self._schema}".screenings s
                JOIN "{self._schema}".movies m ON s.movie_id = m.id
                JOIN "{self._schema}".cinemas c ON s.cinema_id = c.id
                {where_clause}
                ORDER BY s.showtime, s.id
                LIMIT {limit_param} OFFSET {offset_param}
                """,
                *params,
                limit,
                offset,
            )
            if not rows:
                total = await conn.fetchval(
                    f"""
                    SELECT COUNT(*) FROM "{self._schema}".screenings s
                    JOIN "{self._schema}".movies m ON s.movie_id = m.id
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
        params = (cinema_id, _naive_utc(start_date), _naive_utc(end_date))
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
