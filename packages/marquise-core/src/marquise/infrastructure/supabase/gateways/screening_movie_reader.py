"""PostgreSQL movie-first screening projection."""

from __future__ import annotations

from datetime import datetime

import asyncpg

from marquise.infrastructure.supabase.gateways.screening_reader import _naive_utc
from marquise.interface_adapters.repositories.protocols.base import GatewayPage


class SupabaseScreeningMovieReadGateway:
    """Page movies before returning at most three previews per movie."""

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        """Inject the open connection pool and schema."""
        self._pool = pool
        self._schema = schema

    async def search(
        self,
        start: datetime,
        end: datetime | None,
        now: datetime,
        page: int,
        title: str | None = None,
        cinemas: tuple[str, ...] = (),
        languages: tuple[str, ...] = (),
        hours: tuple[tuple[int, int], ...] = (),
        exclude_hours: bool = False,
        excluded_cinemas: tuple[str, ...] = (),
    ) -> GatewayPage:
        """Use one SQL snapshot for eligibility, totals, ordering and previews."""
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                f'''
                WITH qualifying AS (
                    SELECT s.*, c.name AS cinema_name,
                           row_number() OVER (
                               PARTITION BY s.movie_id ORDER BY s.showtime, s.id
                           ) AS rank
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
                _naive_utc(start),
                None if end is None else _naive_utc(end),
                _naive_utc(now),
                None if not title else title.strip(),
                list(cinemas),
                list(languages),
                [start for start, _ in hours],
                [end for _, end in hours],
                exclude_hours,
                list(excluded_cinemas),
                (page - 1) * 24,
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
