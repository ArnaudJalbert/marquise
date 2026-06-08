"""Migration 001: Drop NOT NULL constraint on movies.release_date.

This migration makes the release_date, directors, and cast_members columns
nullable in the movies table, since showtime sources may not provide this info.
"""

from __future__ import annotations

import os

import asyncpg
from dotenv import load_dotenv

from marquise.infrastructure.supabase.database import sanitize_dsn

SCHEMA = "marquise"


async def run() -> None:
    """Execute the migration."""
    load_dotenv()
    dsn = sanitize_dsn(os.environ["DATABASE_URL"])
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(f"""
            ALTER TABLE "{SCHEMA}".movies
                ALTER COLUMN release_date DROP NOT NULL,
                ALTER COLUMN directors DROP NOT NULL,
                ALTER COLUMN cast_members DROP NOT NULL;
        """)
        print("Migration 001: successfully dropped NOT NULL constraints.")
    finally:
        await conn.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
