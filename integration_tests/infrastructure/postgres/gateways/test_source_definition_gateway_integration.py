"""Integration tests for PostgresSourceDefinitionGateway."""

from __future__ import annotations

import pytest

from marquise.infrastructure.postgres.gateways.source_definition import (
    PostgresSourceDefinitionGateway,
)


@pytest.mark.asyncio
async def test_save_and_find_by_name(
    source_definition_gateway: PostgresSourceDefinitionGateway,
) -> None:
    """Verify a source definition can be saved and retrieved by name."""
    g = source_definition_gateway
    result = await g.save(
        name="cineplex",
        display_name="Cineplex",
        description="Cineplex cinemas",
    )
    assert result["name"] == "cineplex"
    assert result["display_name"] == "Cineplex"
    assert result["description"] == "Cineplex cinemas"

    found = await g.find_by_name("cineplex")
    assert found is not None
    assert found["display_name"] == "Cineplex"


@pytest.mark.asyncio
async def test_delete(
    source_definition_gateway: PostgresSourceDefinitionGateway,
) -> None:
    """Verify delete removes the row and returns True."""
    g = source_definition_gateway
    await g.save(name="to-delete", display_name="Delete Me")
    assert await g.delete("to-delete") is True
    assert await g.find_by_name("to-delete") is None


@pytest.mark.asyncio
async def test_delete_missing(
    source_definition_gateway: PostgresSourceDefinitionGateway,
) -> None:
    """Verify delete returns False when no row matches."""
    assert await source_definition_gateway.delete("nonexistent") is False


@pytest.mark.asyncio
async def test_find_all(
    source_definition_gateway: PostgresSourceDefinitionGateway,
) -> None:
    """Verify find_all returns all saved sources."""
    g = source_definition_gateway
    await g.save(name="a-source", display_name="A Source")
    await g.save(name="b-source", display_name="B Source")
    results = await g.find_all()
    assert len(results) >= 2
    names = [r["name"] for r in results]
    assert "a-source" in names
    assert "b-source" in names
