"""Integration tests for SupabaseCinemaSourceAssignmentGateway."""

from __future__ import annotations

import pytest

from marquise.infrastructure.supabase.gateways.cinema import (
    SupabaseCinemaGateway,
)
from marquise.infrastructure.supabase.gateways.cinema_source_assignment import (
    SupabaseCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.supabase.gateways.source_definition import (
    SupabaseSourceDefinitionGateway,
)


async def _seed_parents(
    gateway: SupabaseCinemaGateway,
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Create parent rows needed for FK constraints."""
    await gateway.save(cinema_id="cin-001", name="Cinema One", address=None, city=None)
    await gateway.save(cinema_id="cin-002", name="Cinema Two", address=None, city=None)
    await source_definition_gateway.save(
        name="cineplex", display_name="Cineplex", description=None
    )
    await source_definition_gateway.save(
        name="cinema_du_parc", display_name="Cinema du Parc", description=None
    )


@pytest.mark.asyncio
async def test_assign_and_find(
    assignment_gateway: SupabaseCinemaSourceAssignmentGateway,
    gateway: SupabaseCinemaGateway,
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify an assignment can be upserted and retrieved."""
    await _seed_parents(gateway, source_definition_gateway)
    g = assignment_gateway
    result = await g.assign(cinema_id="cin-001", source_name="cineplex")
    assert result["cinema_id"] == "cin-001"
    assert result["source_name"] == "cineplex"

    found = await g.find_by_cinema_id("cin-001")
    assert found is not None
    assert found["source_name"] == "cineplex"
    assert found["cinema__id"] == "cin-001"
    assert found["source__name"] == "cineplex"


@pytest.mark.asyncio
async def test_assign_upserts_existing(
    assignment_gateway: SupabaseCinemaSourceAssignmentGateway,
    gateway: SupabaseCinemaGateway,
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify reassigning the same cinema updates the source name."""
    await _seed_parents(gateway, source_definition_gateway)
    g = assignment_gateway
    await g.assign(cinema_id="cin-001", source_name="cineplex")
    await g.assign(cinema_id="cin-001", source_name="cinema_du_parc")

    found = await g.find_by_cinema_id("cin-001")
    assert found is not None
    assert found["source_name"] == "cinema_du_parc"


@pytest.mark.asyncio
async def test_unassign(
    assignment_gateway: SupabaseCinemaSourceAssignmentGateway,
    gateway: SupabaseCinemaGateway,
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify unassign removes the row and returns True."""
    await _seed_parents(gateway, source_definition_gateway)
    g = assignment_gateway
    await g.assign(cinema_id="cin-001", source_name="cineplex")
    assert await g.unassign("cin-001") is True
    assert await g.find_by_cinema_id("cin-001") is None


@pytest.mark.asyncio
async def test_unassign_missing(
    assignment_gateway: SupabaseCinemaSourceAssignmentGateway,
) -> None:
    """Verify unassign returns False when no assignment exists."""
    assert await assignment_gateway.unassign("nonexistent") is False


@pytest.mark.asyncio
async def test_find_by_cinema_id_missing(
    assignment_gateway: SupabaseCinemaSourceAssignmentGateway,
) -> None:
    """Verify find_by_cinema_id returns None when no match."""
    result = await assignment_gateway.find_by_cinema_id("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_find_all(
    assignment_gateway: SupabaseCinemaSourceAssignmentGateway,
    gateway: SupabaseCinemaGateway,
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Verify find_all returns all assignments."""
    await _seed_parents(gateway, source_definition_gateway)
    g = assignment_gateway
    await g.assign(cinema_id="cin-001", source_name="cineplex")
    await g.assign(cinema_id="cin-002", source_name="cinema_du_parc")
    results = await g.find_all()
    assert len(results) >= 2
    ids = [r["cinema_id"] for r in results]
    assert "cin-001" in ids
    assert "cin-002" in ids
