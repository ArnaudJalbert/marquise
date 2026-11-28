"""Integration tests for PostgresCinemaSourceAssignmentReadGateway."""

from __future__ import annotations

import asyncpg
import pytest
import pytest_asyncio

from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway
from marquise.infrastructure.postgres.gateways.cinema_source_assignment import (
    PostgresCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.postgres.gateways.cinema_source_assignment_reader import (
    PostgresCinemaSourceAssignmentReadGateway,
)
from marquise.infrastructure.postgres.gateways.source_definition import (
    PostgresSourceDefinitionGateway,
)


@pytest.fixture
def read_gateway(db_pool: asyncpg.Pool) -> PostgresCinemaSourceAssignmentReadGateway:
    """Provide the assignment read gateway over the test schema."""
    return PostgresCinemaSourceAssignmentReadGateway(db_pool, "marquise-test")


@pytest_asyncio.fixture
async def assigned(
    gateway: PostgresCinemaGateway,
    source_definition_gateway: PostgresSourceDefinitionGateway,
    assignment_gateway: PostgresCinemaSourceAssignmentGateway,
) -> None:
    """Assign cineplex to cin-002 and cin-001, and leave cin-003 unassigned."""
    for cinema_id in ("cin-001", "cin-002", "cin-003"):
        await gateway.save(cinema_id=cinema_id, name=cinema_id, address=None, city=None)
    await source_definition_gateway.save(
        name="cineplex", display_name="Cineplex", description=None
    )
    await assignment_gateway.assign(cinema_id="cin-002", source_name="cineplex")
    await assignment_gateway.assign(cinema_id="cin-001", source_name="cineplex")


@pytest.mark.asyncio
@pytest.mark.usefixtures("assigned")
async def test_list_all_returns_rows_ordered_by_cinema(
    read_gateway: PostgresCinemaSourceAssignmentReadGateway,
) -> None:
    """Every assignment comes back with its source names, ordered by cinema ID."""
    rows = await read_gateway.list_all()

    assert rows == [
        {
            "cinema_id": "cin-001",
            "source_name": "cineplex",
            "source_display_name": "Cineplex",
        },
        {
            "cinema_id": "cin-002",
            "source_name": "cineplex",
            "source_display_name": "Cineplex",
        },
    ]


@pytest.mark.asyncio
@pytest.mark.usefixtures("assigned")
async def test_find_by_cinema_id_returns_assigned_row(
    read_gateway: PostgresCinemaSourceAssignmentReadGateway,
) -> None:
    """An assigned cinema returns its source name and display name."""
    assert await read_gateway.find_by_cinema_id("cin-001") == {
        "cinema_id": "cin-001",
        "source_name": "cineplex",
        "source_display_name": "Cineplex",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("assigned")
async def test_find_by_cinema_id_returns_none_when_unassigned(
    read_gateway: PostgresCinemaSourceAssignmentReadGateway,
) -> None:
    """A cinema with no assignment returns None."""
    assert await read_gateway.find_by_cinema_id("cin-003") is None
