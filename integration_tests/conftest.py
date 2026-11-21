"""Integration test fixtures for database-backed gateways."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from marquise.infrastructure.postgres.config import Settings
from marquise.infrastructure.postgres.database import sanitize_dsn
from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway
from marquise.infrastructure.postgres.gateways.cinema_source_assignment import (
    PostgresCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.postgres.gateways.movie import PostgresMovieGateway
from marquise.infrastructure.postgres.gateways.screening import (
    PostgresScreeningGateway,
)
from marquise.infrastructure.postgres.gateways.source_definition import (
    PostgresSourceDefinitionGateway,
)

TEST_SCHEMA = "marquise-test"


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Provide Settings loaded from the environment."""
    load_dotenv()
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        tmdb_api_key=os.environ["TMDB_API_KEY"],
        schema=TEST_SCHEMA,
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
def gateway(db_pool: asyncpg.Pool) -> PostgresCinemaGateway:
    """Provide a PostgresCinemaGateway on the test schema."""
    return PostgresCinemaGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def source_definition_gateway(db_pool: asyncpg.Pool) -> PostgresSourceDefinitionGateway:
    """Provide a PostgresSourceDefinitionGateway on the test schema."""
    return PostgresSourceDefinitionGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def assignment_gateway(db_pool: asyncpg.Pool) -> PostgresCinemaSourceAssignmentGateway:
    """Provide a PostgresCinemaSourceAssignmentGateway on the test schema."""
    return PostgresCinemaSourceAssignmentGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def movie_gateway(db_pool: asyncpg.Pool) -> PostgresMovieGateway:
    """Provide a PostgresMovieGateway on the test schema."""
    return PostgresMovieGateway(pool=db_pool, schema=TEST_SCHEMA)


@pytest.fixture
def screening_gateway(db_pool: asyncpg.Pool) -> PostgresScreeningGateway:
    """Provide a PostgresScreeningGateway on the test schema."""
    return PostgresScreeningGateway(pool=db_pool, schema=TEST_SCHEMA)
