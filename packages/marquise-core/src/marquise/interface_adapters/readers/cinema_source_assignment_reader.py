"""Supabase reader for cinema-source assignment display data."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

from marquise.application.readers import (
    CinemaSourceAssignmentData,
    CinemaSourceAssignmentReader,
)

DEFAULT_SCHEMA = "marquise"


class SupabaseCinemaSourceAssignmentReader(CinemaSourceAssignmentReader):
    """Read cinema-source assignment display data from Supabase."""

    def __init__(self, pool: asyncpg.Pool, schema: str = DEFAULT_SCHEMA) -> None:
        """Initialize with an open connection pool and schema."""
        self._pool = pool
        self._schema = schema

    async def list_all(self) -> list[CinemaSourceAssignmentData]:
        """Return every cinema-source assignment's display data."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT a.cinema_id, sd.display_name AS source_display_name
                FROM "{self._schema}".cinema_source_assignments a
                JOIN "{self._schema}".source_definitions sd
                    ON a.source_name = sd.name
                ORDER BY a.cinema_id
                """
            )
        return [CinemaSourceAssignmentData(**dict(row)) for row in rows]
