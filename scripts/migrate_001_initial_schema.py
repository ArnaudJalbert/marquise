"""Migration 001: Create the initial Marquise database schema.

Creates all 5 tables with foreign key constraints and ``ON DELETE CASCADE``
behaviour.  Designed to be run once on a fresh database.

Schema
------

- ``cinemas`` — movie theatres
- ``movies`` — films
- ``source_definitions`` — registered showtime providers
- ``cinema_source_assignments`` — which source each cinema uses
- ``screenings`` — individual showtimes

Foreign-key relationships are enforced at the database level (no orphan rows).
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
        await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}".cinemas (
                id      TEXT PRIMARY KEY,
                name    TEXT NOT NULL,
                address TEXT,
                city    TEXT,
                website TEXT
            )
        """)
        print("  ✓ cinemas")

        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}".source_definitions (
                name                TEXT PRIMARY KEY,
                display_name        TEXT NOT NULL,
                description         TEXT
            )
        """)
        print("  ✓ source_definitions")

        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}".cinema_source_assignments (
                cinema_id   TEXT PRIMARY KEY
                    REFERENCES "{SCHEMA}".cinemas(id) ON DELETE CASCADE,
                source_name TEXT NOT NULL
                    REFERENCES "{SCHEMA}".source_definitions(name) ON DELETE CASCADE
            )
        """)
        print("  ✓ cinema_source_assignments")

        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}".movies (
                id               TEXT PRIMARY KEY,
                title            TEXT NOT NULL UNIQUE,
                release_year     INTEGER,
                directors        TEXT,
                cast_members     TEXT,
                duration_minutes INTEGER,
                description      TEXT
            )
        """)
        print("  ✓ movies")

        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}".screenings (
                id          TEXT PRIMARY KEY,
                movie_id    TEXT NOT NULL
                    REFERENCES "{SCHEMA}".movies(id) ON DELETE CASCADE,
                cinema_id   TEXT NOT NULL
                    REFERENCES "{SCHEMA}".cinemas(id) ON DELETE CASCADE,
                showtime    TIMESTAMP NOT NULL,
                UNIQUE (cinema_id, movie_id, showtime)
            )
        """)
        print("  ✓ screenings")

        print("Migration 001: initial schema created successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
