"""Integration tests for PostgresCinemaSourceAssignmentGateway."""

from __future__ import annotations

import pytest

from marquise.infrastructure.postgres.gateways.cinema import (
    PostgresCinemaGateway,
)
from marquise.infrastructure.postgres.gateways.cinema_source_assignment import (
    PostgresCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.postgres.gateways.source_definition import (
    PostgresSourceDefinitionGateway,
)


async def _seed_parents(
    gateway: PostgresCinemaGateway,
    source_definition_gateway: PostgresSourceDefinitionGateway,
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
    assignment_gateway: PostgresCinemaSourceAssignmentGateway,
    gateway: PostgresCinemaGateway,
    source_definition_gateway: PostgresSourceDefinitionGateway,
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
    assignment_gateway: PostgresCinemaSourceAssignmentGateway,
    gateway: PostgresCinemaGateway,
    source_definition_gateway: PostgresSourceDefinitionGateway,
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
    assignment_gateway: PostgresCinemaSourceAssignmentGateway,
    gateway: PostgresCinemaGateway,
    source_definition_gateway: PostgresSourceDefinitionGateway,
) -> None:
    """Verify unassign removes the row and returns True."""
    await _seed_parents(gateway, source_definition_gateway)
    g = assignment_gateway
    await g.assign(cinema_id="cin-001", source_name="cineplex")
    assert await g.unassign("cin-001") is True
    assert await g.find_by_cinema_id("cin-001") is None


@pytest.mark.asyncio
async def test_unassign_missing(
    assignment_gateway: PostgresCinemaSourceAssignmentGateway,
) -> None:
    """Verify unassign returns False when no assignment exists."""
    assert await assignment_gateway.unassign("nonexistent") is False
