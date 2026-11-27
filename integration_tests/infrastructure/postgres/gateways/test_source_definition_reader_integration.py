"""Integration tests for PostgresSourceDefinitionReadGateway."""

from __future__ import annotations

import asyncpg
import pytest

from marquise.infrastructure.postgres.gateways.source_definition import (
    PostgresSourceDefinitionGateway,
)
from marquise.infrastructure.postgres.gateways.source_definition_reader import (
    PostgresSourceDefinitionReadGateway,
)


@pytest.mark.asyncio
async def test_list_all_returns_every_source_ordered_by_name(
    db_pool: asyncpg.Pool,
    source_definition_gateway: PostgresSourceDefinitionGateway,
) -> None:
    """Every saved source comes back as a plain row, ordered by name."""
    await source_definition_gateway.save(name="b-source", display_name="B Source")
    await source_definition_gateway.save(
        name="a-source", display_name="A Source", description="First"
    )

    rows = await PostgresSourceDefinitionReadGateway(
        db_pool, "marquise-test"
    ).list_all()

    assert rows == [
        {"name": "a-source", "display_name": "A Source", "description": "First"},
        {"name": "b-source", "display_name": "B Source", "description": None},
    ]


@pytest.mark.asyncio
async def test_list_all_returns_empty_list_without_sources(
    db_pool: asyncpg.Pool,
) -> None:
    """An empty source_definitions table gives no rows."""
    rows = await PostgresSourceDefinitionReadGateway(
        db_pool, "marquise-test"
    ).list_all()

    assert rows == []
