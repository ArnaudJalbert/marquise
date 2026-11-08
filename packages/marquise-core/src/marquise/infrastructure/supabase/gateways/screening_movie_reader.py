"""PostgreSQL movie-first screening projection."""

from __future__ import annotations

from datetime import datetime

import asyncpg

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.infrastructure.supabase.gateways.screening_reader import _naive_utc
from marquise.interface_adapters.repositories.protocols.base import GatewayPage

type _FilterRequest = (
    ScreeningMovieReader.SearchRequest | ScreeningMovieReader.DayCountRequest
)


class SupabaseScreeningMovieReadGateway:
    """Page movies or count days over one shared qualifying-screening filter."""

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        """Inject the open connection pool and schema."""
        self._pool = pool
        self._schema = schema

    async def search(self, request: ScreeningMovieReader.SearchRequest) -> GatewayPage:
        """Use one SQL snapshot for eligibility, totals, ordering and previews."""
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                f'''
                WITH qualifying AS (
                    SELECT s.*, c.name AS cinema_name,
                           row_number() OVER (
                               PARTITION BY s.movie_id ORDER BY s.showtime, s.id
                           ) AS rank
                    {self._build_qualifying_screenings_sql()}
                ), eligible AS (
                    SELECT movie_id, showtime AS next_showtime
                    FROM qualifying WHERE rank = 1
                ), selected AS (
                    SELECT * FROM eligible
                    ORDER BY next_showtime, movie_id LIMIT 24 OFFSET $11
                )
                SELECT totals.total, m.id, m.title, m.release_year, m.directors,
                       m.duration_minutes, m.description, m.poster_url,
                       m.tmdb_rating, m.tmdb_vote_count,
                       q.id AS screening_id, q.cinema_id, q.cinema_name,
                       q.showtime, q.language, q.ticket_url, q.room
                FROM (SELECT count(*) AS total FROM eligible) totals
                LEFT JOIN selected p ON true
                LEFT JOIN "{self._schema}".movies m ON m.id = p.movie_id
                LEFT JOIN qualifying q ON q.movie_id = p.movie_id AND q.rank <= 3
                ORDER BY p.next_showtime, p.movie_id, q.showtime, q.id
                ''',
                *self._bind_filter_arguments(request),
                (request.page - 1) * 24,
            )
        movies: dict[str, dict] = {}
        for row in rows:
            if row["id"] is None:
                continue
            movie = movies.setdefault(
                row["id"],
                {
                    key: row[key]
                    for key in (
                        "id",
                        "title",
                        "release_year",
                        "directors",
                        "duration_minutes",
                        "description",
                        "poster_url",
                        "tmdb_rating",
                        "tmdb_vote_count",
                    )
                },
            )
            movie.setdefault("screenings", []).append(
                {
                    "id": row["screening_id"],
                    "movie_id": row["id"],
                    "movie_title": row["title"],
                    "cinema_id": row["cinema_id"],
                    "cinema_name": row["cinema_name"],
                    "showtime": row["showtime"],
                    "language": row["language"],
                    "ticket_url": row["ticket_url"],
                    "room": row["room"],
                }
            )
        return GatewayPage(rows=list(movies.values()), total=rows[0]["total"])

    async def count_days(
        self, request: ScreeningMovieReader.DayCountRequest
    ) -> list[dict]:
        """Count every qualifying screening per Montréal date in one SQL query."""
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                f"""
                SELECT ((s.showtime AT TIME ZONE 'UTC')
                        AT TIME ZONE 'America/Montreal')::date AS day,
                       count(*)::int AS screenings
                {self._build_qualifying_screenings_sql()}
                GROUP BY day ORDER BY day
                """,
                *self._bind_filter_arguments(request),
            )
        return [dict(row) for row in rows]

    def _build_qualifying_screenings_sql(self) -> str:
        """Return the listing's FROM and WHERE clauses over arguments $1 to $10."""
        return f'''
            FROM "{self._schema}".screenings s
            JOIN "{self._schema}".cinemas c ON c.id = s.cinema_id
            JOIN "{self._schema}".movies m ON m.id = s.movie_id
            WHERE s.showtime >= $1
              AND ($2::timestamp IS NULL OR s.showtime <= $2)
              AND s.showtime > $3
              AND ($4::text IS NULL OR m.title ILIKE '%' || $4 || '%')
              AND (cardinality($5::text[]) = 0 OR s.cinema_id = ANY($5))
              AND (cardinality($6::text[]) = 0 OR s.language = ANY($6))
              AND (cardinality($7::int[]) = 0 OR EXISTS (
                   SELECT 1 FROM unnest($7::int[], $8::int[]) h(lo, hi)
                   WHERE int4range(h.lo, h.hi) @> extract(
                       hour FROM (s.showtime AT TIME ZONE 'UTC')
                           AT TIME ZONE 'America/Montreal'
                   )::int
                   ) <> $9::boolean)
              AND NOT s.cinema_id = ANY($10::text[])
        '''

    @staticmethod
    def _bind_filter_arguments(
        request: _FilterRequest,
    ) -> tuple[datetime | str | list[str] | list[int] | bool | None, ...]:
        """Return the values bound to the shared filter's $1 to $10."""
        hour_filter = request.hours
        hour_ranges = hour_filter.ranges if hour_filter else ()
        return (
            _naive_utc(request.start),
            None if request.end is None else _naive_utc(request.end),
            _naive_utc(request.now),
            None if not request.title else request.title.strip(),
            list(request.cinemas),
            list(request.languages),
            [item.start for item in hour_ranges],
            [item.end for item in hour_ranges],
            hour_filter is not None and hour_filter.excluded,
            list(request.excluded_cinemas),
        )
