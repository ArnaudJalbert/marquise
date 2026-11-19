"""Atomic PostgreSQL metadata persistence, without selection or merge policy."""

from datetime import datetime

from asyncpg.exceptions import UniqueViolationError

from marquise.infrastructure.postgres.connection_pool import ConnectionPool
from marquise.interface_adapters.repositories.protocols.movie_metadata import (
    MovieMetadataConflictError,
)

# Storage column names are fixed here, never taken from a caller's SQL fragment.
_PATCH_COLUMNS = (
    "title",
    "original_title",
    "description",
    "release_year",
    "directors",
    "cast_members",
    "duration_minutes",
    "genres",
    "origin_countries",
    "poster_url",
    "trailer_url",
    "rating",
    "tmdb_rating",
    "tmdb_vote_count",
)


class PostgresMovieMetadataGateway:
    """Snapshot and compare-and-patch operations on existing stable movie IDs."""

    def __init__(self, pool: ConnectionPool, schema: str = "marquise") -> None:
        self._pool = pool
        quoted = schema.replace('"', '""')
        self._movies = f'"{quoted}".movies'
        self._screenings = f'"{quoted}".screenings'
        self._revisions = f'"{quoted}".movie_reference_revisions'

    def _select(self) -> str:
        # Committed transaction markers include reference edits and deletions.
        # xmin also distinguishes a deleted and recreated row with the same ID.
        return f"""
            SELECT m.*,
                md5(row_to_json(m)::text || m.xmin::text ||
                    r.revision::text) AS revision,
                ARRAY(SELECT s.id FROM {self._screenings} s
                      WHERE s.movie_id = m.id ORDER BY s.id) AS screening_ids
            FROM {self._movies} m
            CROSS JOIN LATERAL (
                SELECT count(*) AS revision FROM {self._revisions} refs
                WHERE refs.movie_id = m.id
            ) r
        """

    async def get(self, movie_id: str) -> dict | None:
        """Read metadata and references in one consistent statement snapshot."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(self._select() + " WHERE m.id = $1", movie_id)
        return dict(row) if row is not None else None

    async def find_by_tmdb_id(self, tmdb_id: str) -> dict | None:
        """Read an explicitly TMDB-labelled identity using the unique mapping."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                self._select() + " WHERE m.tmdb_id = $1",
                tmdb_id,
            )
        return dict(row) if row is not None else None

    async def list_tmdb_movies(self) -> list[dict]:
        """List all known TMDB identities, including unenriched legacy movies."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                self._select() + " WHERE m.tmdb_id IS NOT NULL ORDER BY m.id",
            )
        return [dict(row) for row in rows]

    async def update_metadata(
        self,
        movie_id: str,
        revision: str,
        values: dict,
        tmdb_id: str,
        enriched_at: datetime,
    ) -> dict:
        """Lock the target and reject stale or conflicting writes atomically."""
        if not tmdb_id.strip():
            raise ValueError("TMDB ID must be nonempty")
        if enriched_at.tzinfo is None or enriched_at.utcoffset() is None:
            raise ValueError("Enrichment timestamp must be timezone-aware")
        assignments = ", ".join(
            f"{column} = COALESCE(${index}, {column})"
            for index, column in enumerate(_PATCH_COLUMNS, start=4)
        )
        try:
            async with self._pool.acquire() as conn, conn.transaction():
                await conn.fetchrow(
                    f"SELECT id FROM {self._movies} WHERE id = $1 FOR UPDATE",
                    movie_id,
                )
                current = await conn.fetchrow(
                    self._select() + " WHERE m.id = $1",
                    movie_id,
                )
                if current is None or current["revision"] != revision:
                    raise MovieMetadataConflictError(
                        "Movie snapshot is stale or missing"
                    )
                if current["tmdb_id"] not in (None, tmdb_id):
                    raise MovieMetadataConflictError(
                        "Movie has a different TMDB identity"
                    )
                await conn.execute(
                    f"UPDATE {self._movies} SET {assignments}, "
                    "tmdb_id = $2, metadata_enriched_at = $3 WHERE id = $1",
                    movie_id,
                    tmdb_id,
                    enriched_at,
                    *(values.get(column) for column in _PATCH_COLUMNS),
                )
                result = await conn.fetchrow(
                    self._select() + " WHERE m.id = $1",
                    movie_id,
                )
                return dict(result)
        except UniqueViolationError as exc:
            raise MovieMetadataConflictError(
                "Movie title or TMDB identity belongs to another movie"
            ) from exc
