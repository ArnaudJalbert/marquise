"""Copy configuration from a read-only snapshot into an empty catalog database.

Run with ``uv run python scripts/transfer_cinema_configuration.py`` from repo root.
Credentials come only from SOURCE_DATABASE_URL and TARGET_DATABASE_URL. URLs must
be percent-encoded. No .env file is loaded and DATABASE_URL is never a fallback.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

CONFIGURATION = {
    "cinemas": ("id", "name", "address", "city", "website"),
    "source_definitions": ("name", "display_name", "description"),
    "cinema_source_assignments": ("cinema_id", "source_name"),
}
EXCLUDED = ("movies", "screenings")


class TransferError(Exception):
    """A credential-free explanation of why the transfer was refused."""


async def transfer(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> dict[str, int]:
    """Verify and commit only configuration, leaving the source untouched."""
    async with source.transaction(isolation="repeatable_read", readonly=True):
        rows = {
            table: await source.fetch(
                f"SELECT {', '.join(columns)} FROM marquise.{table} "
                f"ORDER BY {columns[0]}"
            )
            for table, columns in CONFIGURATION.items()
        }
    async with target.transaction():
        await target.execute("SET LOCAL lock_timeout = '5s'")
        await target.execute("SET LOCAL statement_timeout = '60s'")
        await target.execute(
            Path(__file__).with_name("marquise-schema.sql").read_text()
        )
        # Hold the empty-destination check through commit, including excluded data.
        tables = (*CONFIGURATION, *EXCLUDED)
        await target.execute(
            "LOCK TABLE "
            + ", ".join(f"marquise.{table}" for table in tables)
            + " IN ACCESS EXCLUSIVE MODE"
        )
        for table in tables:
            if await target.fetchval(f"SELECT EXISTS (SELECT 1 FROM marquise.{table})"):
                raise TransferError(f"Destination must be empty: {table} contains rows")
        for table, columns in CONFIGURATION.items():
            if rows[table]:
                placeholders = ", ".join(f"${i}" for i in range(1, len(columns) + 1))
                await target.executemany(
                    f"INSERT INTO marquise.{table} ({', '.join(columns)}) "
                    f"VALUES ({placeholders})",
                    rows[table],
                )
            copied = await target.fetch(
                f"SELECT {', '.join(columns)} FROM marquise.{table} "
                f"ORDER BY {columns[0]}"
            )
            if copied != rows[table]:
                raise TransferError(f"Configuration verification failed: {table}")
        for table in EXCLUDED:
            if await target.fetchval(f"SELECT EXISTS (SELECT 1 FROM marquise.{table})"):
                raise TransferError(f"Excluded table is not empty: {table}")
    return {table: len(records) for table, records in rows.items()}


async def main() -> None:
    """Connect with explicit environment credentials and report verified counts."""
    source_url = os.environ["SOURCE_DATABASE_URL"]
    target_url = os.environ["TARGET_DATABASE_URL"]
    if source_url == target_url:
        raise TransferError("Source and destination must be different databases")
    source = await asyncpg.connect(source_url, timeout=20)
    try:
        target = await asyncpg.connect(target_url, timeout=20)
        try:
            counts = await transfer(source, target)
            print(
                json.dumps(
                    {"configuration": counts, "excluded": dict.fromkeys(EXCLUDED, 0)}
                )
            )
        finally:
            await target.close()
    finally:
        await source.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except TransferError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (
        KeyError,
        ValueError,
        OSError,
        asyncpg.PostgresError,
        TimeoutError,
    ) as error:
        # Connection errors can contain credentials. Never print their messages.
        print(
            f"Transfer failed ({type(error).__name__}); check configuration/access.",
            file=sys.stderr,
        )
        sys.exit(1)
