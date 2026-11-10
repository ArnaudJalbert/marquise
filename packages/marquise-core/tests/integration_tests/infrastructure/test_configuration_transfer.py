"""Exercise the operator transfer command against disposable PostgreSQL databases."""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio

from marquise.infrastructure.supabase.config import Settings
from marquise.infrastructure.supabase.database import sanitize_dsn

SCRIPTS = Path(__file__).resolve().parents[5] / "scripts"


@pytest_asyncio.fixture
async def databases(settings: Settings) -> AsyncIterator[tuple[str, str]]:
    """Create two isolated databases without touching the configured catalog."""
    dsn = sanitize_dsn(settings.database_url)
    admin = await asyncpg.connect(dsn)
    names = [f"transfer_{uuid4().hex}" for _ in range(2)]
    try:
        for name in names:
            await admin.execute(f'CREATE DATABASE "{name}"')
        parts = urlsplit(dsn)
        urls = [urlunsplit(parts._replace(path=f"/{name}")) for name in names]
        yield urls[0], urls[1]
    finally:
        for name in names:
            await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.close()


async def run_transfer(source: str, target: str) -> tuple[int, str]:
    """Invoke the same environment-only command used by operators."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(SCRIPTS / "transfer_cinema_configuration.py"),
        env={
            **os.environ,
            "SOURCE_DATABASE_URL": source,
            "TARGET_DATABASE_URL": target,
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output, _ = await process.communicate()
    return await process.wait(), output.decode()


async def seed_source(conn: asyncpg.Connection) -> None:
    """Provide configuration and catalog/history that must stay at the source."""
    await conn.execute((SCRIPTS / "marquise-schema.sql").read_text())
    await conn.execute("""
        INSERT INTO marquise.cinemas VALUES
            ('cinema-original-id', 'Cinéma test', '123 rue Test', 'Montréal',
             'https://cinema.example');
        INSERT INTO marquise.source_definitions VALUES
            ('provider', 'Provider', 'Configuration to preserve');
        INSERT INTO marquise.cinema_source_assignments VALUES
            ('cinema-original-id', 'provider');
        INSERT INTO marquise.movies (id, title, tmdb_id)
            VALUES ('old-movie', 'Old catalog', '123');
        INSERT INTO marquise.screenings (id, movie_id, cinema_id, showtime)
            VALUES ('old-screening', 'old-movie', 'cinema-original-id', '2026-10-30');
    """)


@pytest.mark.asyncio
async def test_transfer_preserves_configuration_and_excludes_catalog(
    databases: tuple[str, str],
) -> None:
    """Fresh bootstrap copies exact configuration, preserves source, refuses replay."""
    source = await asyncpg.connect(databases[0])
    target = await asyncpg.connect(databases[1])
    try:
        await seed_source(source)
        code, output = await run_transfer(*databases)
        assert code == 0, output
        for table, key in (
            ("cinemas", "id"),
            ("source_definitions", "name"),
            ("cinema_source_assignments", "cinema_id"),
        ):
            query = f"SELECT * FROM marquise.{table} ORDER BY {key}"
            assert await target.fetch(query) == await source.fetch(query)
            assert await target.fetchval(f"SELECT count(*) FROM marquise.{table}") == 1
        for table in (
            "movies",
            "screenings",
        ):
            assert await target.fetchval(f"SELECT count(*) FROM marquise.{table}") == 0
            assert await source.fetchval(f"SELECT count(*) FROM marquise.{table}") == 1
        assert (
            await target.fetchval("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_schema = 'marquise' AND table_name = 'movies'
            AND column_name = 'tmdb_id'
        """)
            == 1
        )
        code, output = await run_transfer(*databases)
        assert code != 0
        assert "empty" in output
        assert await target.fetchval("SELECT count(*) FROM marquise.cinemas") == 1
    finally:
        await source.close()
        await target.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["movies", "source_definitions"])
async def test_transfer_refuses_existing_destination_data(
    databases: tuple[str, str], table: str
) -> None:
    """Any existing catalog, history, or configuration aborts without changing rows."""
    source = await asyncpg.connect(databases[0])
    target = await asyncpg.connect(databases[1])
    try:
        await seed_source(source)
        await seed_source(target)
        await target.execute("""
            TRUNCATE marquise.screenings, marquise.movies,
                marquise.cinema_source_assignments, marquise.cinemas,
                marquise.source_definitions
        """)
        statements = {
            "movies": "INSERT INTO marquise.movies (id, title) VALUES ('keep', 'Keep')",
            "source_definitions": "INSERT INTO marquise.source_definitions "
            "VALUES ('keep', 'Keep', NULL)",
        }
        await target.execute(statements[table])
        code, output = await run_transfer(*databases)
        assert code != 0
        assert "empty" in output
        assert await target.fetchval(f"SELECT count(*) FROM marquise.{table}") == 1
        assert await target.fetchval("SELECT count(*) FROM marquise.cinemas") == 0
    finally:
        await source.close()
        await target.close()


@pytest.mark.asyncio
async def test_failed_transfer_rolls_back_all_configuration(
    databases: tuple[str, str],
) -> None:
    """A destination constraint failure leaves no partially copied configuration."""
    source = await asyncpg.connect(databases[0])
    target = await asyncpg.connect(databases[1])
    try:
        await seed_source(source)
        await target.execute((SCRIPTS / "marquise-schema.sql").read_text())
        await target.execute("""
            ALTER TABLE marquise.source_definitions
            ADD CONSTRAINT reject_description CHECK (description IS NULL)
        """)
        code, output = await run_transfer(*databases)
        assert code != 0
        assert "CheckViolationError" in output
        assert await target.fetchval("SELECT count(*) FROM marquise.cinemas") == 0
        assert await source.fetchval("SELECT count(*) FROM marquise.cinemas") == 1
    finally:
        await source.close()
        await target.close()


@pytest.mark.asyncio
async def test_tmdb_schema_upgrade_preserves_existing_movie(
    databases: tuple[str, str],
) -> None:
    """The merged TMDB migration upgrades the previous schema without matching rows."""
    conn = await asyncpg.connect(databases[1])
    try:
        previous = (
            (SCRIPTS / "marquise-schema.sql")
            .read_text()
            .replace(
                "origin_countries TEXT,\n    tmdb_id          TEXT UNIQUE",
                "origin_countries TEXT",
            )
        )
        await conn.execute(previous)
        await conn.execute(
            "INSERT INTO marquise.movies (id, title) VALUES ('keep', 'Keep')"
        )
        migration = (SCRIPTS / "migrations/321-add-movies-tmdb-id.sql").read_text()
        await conn.execute(migration)
        await conn.execute(migration)
        assert tuple(
            await conn.fetchrow("SELECT id, title, tmdb_id FROM marquise.movies")
        ) == ("keep", "Keep", None)
        await conn.execute("UPDATE marquise.movies SET tmdb_id = '123'")
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                "INSERT INTO marquise.movies (id, title, tmdb_id) "
                "VALUES ('duplicate', 'Other title', '123')"
            )
    finally:
        await conn.close()
