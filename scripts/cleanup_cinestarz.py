"""Remove Cine Starz screenings and orphaned movies.

Dry-run by default. Execute with:
    uv run python scripts/cleanup_cinestarz.py --execute
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re

import asyncpg
from dotenv import load_dotenv

from marquise.infrastructure.supabase.database import sanitize_dsn


async def cleanup(*, execute: bool, schema: str) -> None:
    table_cinemas = f'"{schema}".cinemas'
    table_assignments = f'"{schema}".cinema_source_assignments'
    table_screenings = f'"{schema}".screenings'
    table_movies = f'"{schema}".movies'

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    conn = await asyncpg.connect(sanitize_dsn(database_url))
    try:
        async with conn.transaction():
            cinemas = await conn.fetch(
                f"""
                SELECT c.id, c.name
                FROM {table_cinemas} c
                JOIN {table_assignments} a ON a.cinema_id = c.id
                WHERE a.source_name = 'cinestarz'
                ORDER BY c.name
                """
            )
            if not cinemas:
                raise RuntimeError("No cinemas assigned to source 'cinestarz'")

            cinema_ids = [row["id"] for row in cinemas]
            screening_count = await conn.fetchval(
                f"""
                SELECT count(*)
                FROM {table_screenings}
                WHERE cinema_id = ANY($1::text[])
                """,
                cinema_ids,
            )
            movie_rows = await conn.fetch(
                f"""
                SELECT DISTINCT m.id, m.title
                FROM {table_screenings} s
                JOIN {table_movies} m ON m.id = s.movie_id
                WHERE s.cinema_id = ANY($1::text[])
                ORDER BY m.title
                """,
                cinema_ids,
            )
            orphan_rows = await conn.fetch(
                f"""
                SELECT m.id, m.title
                FROM {table_movies} m
                WHERE m.id = ANY($1::text[])
                  AND NOT EXISTS (
                      SELECT 1
                      FROM {table_screenings} s
                      WHERE s.movie_id = m.id
                        AND s.cinema_id <> ALL($2::text[])
                  )
                ORDER BY m.title
                """,
                [row["id"] for row in movie_rows],
                cinema_ids,
            )

            print("Cine Starz cinemas:", ", ".join(row["name"] for row in cinemas))
            print(f"Screenings to delete: {screening_count}")
            print(f"Movies to delete: {len(orphan_rows)}")
            for row in orphan_rows:
                print(f"  - {row['title']} ({row['id']})")

            if not execute:
                print("Dry run. Nothing deleted. Use --execute to commit.")
                return

            deleted_screenings = await conn.fetchval(
                f"""
                WITH deleted AS (
                    DELETE FROM {table_screenings}
                    WHERE cinema_id = ANY($1::text[])
                    RETURNING id
                )
                SELECT count(*) FROM deleted
                """,
                cinema_ids,
            )
            deleted_movies = await conn.fetchval(
                f"""
                WITH deleted AS (
                    DELETE FROM {table_movies}
                    WHERE id = ANY($1::text[])
                    RETURNING id
                )
                SELECT count(*) FROM deleted
                """,
                [row["id"] for row in orphan_rows],
            )
            print(f"Deleted screenings: {deleted_screenings}")
            print(f"Deleted movies: {deleted_movies}")
    finally:
        await conn.close()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="commit deletion; without this flag, only show what would be deleted",
    )
    parser.add_argument(
        "--schema",
        default=os.environ.get("DATABASE_SCHEMA", "marquise"),
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.schema):
        parser.error("schema must be a valid PostgreSQL identifier")
    asyncio.run(cleanup(execute=args.execute, schema=args.schema))


if __name__ == "__main__":
    main()
