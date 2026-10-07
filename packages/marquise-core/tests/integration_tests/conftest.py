"""Integration test fixtures for database-backed gateways."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from marquise.infrastructure.supabase.config import Settings
from marquise.infrastructure.supabase.database import sanitize_dsn
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.cinema_source_assignment import (
    SupabaseCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)
from marquise.infrastructure.supabase.gateways.source_definition import (
    SupabaseSourceDefinitionGateway,
)

TEST_SCHEMA = "marquise-test"


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Provide Settings loaded from the environment."""
    load_dotenv()
    return Settings(
        database_url=os.environ["DATABASE_URL"],
    )


@pytest_asyncio.fixture
async def db_pool(
    settings: Settings,
) -> AsyncIterator[asyncpg.Pool]:
    """Provide a clean asyncpg pool with a test schema and table."""
    pool = await asyncpg.create_pool(
        sanitize_dsn(settings.database_url), min_size=1, max_size=2
    )
    async with pool.acquire() as conn:
        await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{TEST_SCHEMA}"')
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{TEST_SCHEMA}".cinemas (
                id      TEXT PRIMARY KEY,
                name    TEXT NOT NULL,
                address TEXT,
                city    TEXT,
                website TEXT
            )
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{TEST_SCHEMA}".source_definitions (
                name                TEXT PRIMARY KEY,
                display_name        TEXT NOT NULL,
                description         TEXT
            )
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{TEST_SCHEMA}".cinema_source_assignments (
                cinema_id   TEXT PRIMARY KEY
                    REFERENCES "{TEST_SCHEMA}".cinemas(id) ON DELETE CASCADE,
                source_name TEXT NOT NULL
                    REFERENCES "{TEST_SCHEMA}".source_definitions(name)
                    ON DELETE CASCADE
            )
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{TEST_SCHEMA}".movies (
                id               TEXT PRIMARY KEY,
                title            TEXT NOT NULL UNIQUE,
                release_year     INTEGER,
                directors        TEXT,
                cast_members     TEXT,
                duration_minutes INTEGER,
                description      TEXT,
                poster_url       TEXT,
                trailer_url      TEXT,
                genres           TEXT,
                original_title   TEXT,
                rating           TEXT,
                origin_countries TEXT
            )
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{TEST_SCHEMA}".screenings (
                id          TEXT PRIMARY KEY,
                movie_id    TEXT NOT NULL
                    REFERENCES "{TEST_SCHEMA}".movies(id) ON DELETE CASCADE,
                cinema_id   TEXT NOT NULL
                    REFERENCES "{TEST_SCHEMA}".cinemas(id) ON DELETE CASCADE,
                showtime    TIMESTAMP NOT NULL,
                external_id TEXT,
                ticket_url  TEXT,
                room        TEXT,
                language    TEXT,
                UNIQUE (cinema_id, movie_id, showtime),
                CONSTRAINT screenings_external_id_key UNIQUE (cinema_id, external_id)
            )
            """
        )
    async with pool.acquire() as conn:
        await conn.execute(
            f'''TRUNCATE TABLE
                "{TEST_SCHEMA}".screenings,
                "{TEST_SCHEMA}".cinema_source_assignments,
                "{TEST_SCHEMA}".movies,
                "{TEST_SCHEMA}".cinemas,
                "{TEST_SCHEMA}".source_definitions
                CASCADE'''
        )
    yield pool
    await pool.close()


@pytest_asyncio.fixture
async def gateway(db_pool: asyncpg.Pool) -> AsyncIterator[SupabaseCinemaGateway]:
    """Provide a SupabaseCinemaGateway with a clean test table."""
    async with db_pool.acquire() as conn:
        await conn.execute(f'DELETE FROM "{TEST_SCHEMA}".cinemas')
    yield SupabaseCinemaGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest_asyncio.fixture
async def source_definition_gateway(
    db_pool: asyncpg.Pool,
) -> AsyncIterator[SupabaseSourceDefinitionGateway]:
    """Provide a SupabaseSourceDefinitionGateway with a clean test table."""
    async with db_pool.acquire() as conn:
        await conn.execute(f'DELETE FROM "{TEST_SCHEMA}".source_definitions')
    yield SupabaseSourceDefinitionGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest_asyncio.fixture
async def assignment_gateway(
    db_pool: asyncpg.Pool,
) -> AsyncIterator[SupabaseCinemaSourceAssignmentGateway]:
    """Provide a SupabaseCinemaSourceAssignmentGateway with a clean table."""
    async with db_pool.acquire() as conn:
        await conn.execute(f'DELETE FROM "{TEST_SCHEMA}".cinema_source_assignments')
    yield SupabaseCinemaSourceAssignmentGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest_asyncio.fixture
async def movie_gateway(
    db_pool: asyncpg.Pool,
) -> AsyncIterator[SupabaseMovieGateway]:
    """Provide a SupabaseMovieGateway with a clean test table."""
    async with db_pool.acquire() as conn:
        await conn.execute(f'DELETE FROM "{TEST_SCHEMA}".movies')
    yield SupabaseMovieGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest_asyncio.fixture
async def screening_gateway(
    db_pool: asyncpg.Pool,
) -> AsyncIterator[SupabaseScreeningGateway]:
    """Provide a SupabaseScreeningGateway with a clean test table."""
    async with db_pool.acquire() as conn:
        await conn.execute(f'DELETE FROM "{TEST_SCHEMA}".screenings')
    yield SupabaseScreeningGateway(pool=db_pool, schema=TEST_SCHEMA)
