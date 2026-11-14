"""Integration test fixtures for database-backed gateways."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

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
        schema = (
            (Path(__file__).resolve().parents[1] / "scripts/marquise-schema.sql")
            .read_text()
            .replace(
                "CREATE SCHEMA IF NOT EXISTS marquise;",
                f'CREATE SCHEMA IF NOT EXISTS "{TEST_SCHEMA}";',
            )
            .replace("marquise.", f'"{TEST_SCHEMA}".')
        )
        await conn.execute(schema)
        await conn.execute(
            f'''TRUNCATE TABLE
                "{TEST_SCHEMA}".movie_reference_revisions,
                "{TEST_SCHEMA}".screenings,
                "{TEST_SCHEMA}".cinema_source_assignments,
                "{TEST_SCHEMA}".movies,
                "{TEST_SCHEMA}".cinemas,
                "{TEST_SCHEMA}".source_definitions
                CASCADE'''
        )
    yield pool
    await pool.close()


@pytest.fixture
def gateway(db_pool: asyncpg.Pool) -> SupabaseCinemaGateway:
    """Provide a SupabaseCinemaGateway on the test schema."""
    return SupabaseCinemaGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def source_definition_gateway(db_pool: asyncpg.Pool) -> SupabaseSourceDefinitionGateway:
    """Provide a SupabaseSourceDefinitionGateway on the test schema."""
    return SupabaseSourceDefinitionGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def assignment_gateway(db_pool: asyncpg.Pool) -> SupabaseCinemaSourceAssignmentGateway:
    """Provide a SupabaseCinemaSourceAssignmentGateway on the test schema."""
    return SupabaseCinemaSourceAssignmentGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def movie_gateway(db_pool: asyncpg.Pool) -> SupabaseMovieGateway:
    """Provide a SupabaseMovieGateway on the test schema."""
    return SupabaseMovieGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def screening_gateway(db_pool: asyncpg.Pool) -> SupabaseScreeningGateway:
    """Provide a SupabaseScreeningGateway on the test schema."""
    return SupabaseScreeningGateway(pool=db_pool, schema=TEST_SCHEMA)
