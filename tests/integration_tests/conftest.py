"""Integration test fixtures for database-backed gateways."""

from __future__ import annotations

import os
from typing import AsyncIterator

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
        supabase_url=os.environ.get("SUPABASE_URL", ""),
        supabase_publishable_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY", ""),
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
                cinema_id   TEXT PRIMARY KEY,
                source_name TEXT NOT NULL
            )
            """
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
