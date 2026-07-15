"""Integration tests for SupabaseSourceDefinitionGateway."""

from __future__ import annotations

import pytest

from marquise.infrastructure.supabase.gateways.source_definition import (
    SupabaseSourceDefinitionGateway,
)


@pytest.mark.asyncio
async def test_save_and_find_by_name(
    source_definition_gateway: SupabaseSourceDefinitionGateway,
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
async def test_find_by_name_missing(
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify find_by_name returns None when no match exists."""
    result = await source_definition_gateway.find_by_name("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_exists_by_name(
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify exists_by_name returns True after saving a source."""
    g = source_definition_gateway
    await g.save(name="test-source", display_name="Test Source")
    assert await g.exists_by_name("test-source") is True
    assert await g.exists_by_name("missing") is False


@pytest.mark.asyncio
async def test_delete(
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify delete removes the row and returns True."""
    g = source_definition_gateway
    await g.save(name="to-delete", display_name="Delete Me")
    assert await g.delete("to-delete") is True
    assert await g.find_by_name("to-delete") is None


@pytest.mark.asyncio
async def test_delete_missing(
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify delete returns False when no row matches."""
    assert await source_definition_gateway.delete("nonexistent") is False


@pytest.mark.asyncio
async def test_find_all(
    source_definition_gateway: SupabaseSourceDefinitionGateway,
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
