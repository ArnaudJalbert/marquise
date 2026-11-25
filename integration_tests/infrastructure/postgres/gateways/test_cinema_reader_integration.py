"""Integration tests for PostgresCinemaReadGateway SQL."""

from __future__ import annotations

import asyncpg
import pytest

from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway
from marquise.infrastructure.postgres.gateways.cinema_reader import (
    PostgresCinemaReadGateway,
)


@pytest.fixture
def reader(db_pool: asyncpg.Pool) -> PostgresCinemaReadGateway:
    """Provide the cinema reader over the test schema."""
    return PostgresCinemaReadGateway(db_pool, "marquise-test")


@pytest.mark.asyncio
async def test_find_by_id_returns_display_row(
    reader: PostgresCinemaReadGateway, gateway: PostgresCinemaGateway
) -> None:
    """A stored cinema comes back as one plain row with its display columns."""
    await gateway.save(
        cinema_id="cin-001", name="Cinema One", address="1 Rue", city="Montréal"
    )

    row = await reader.find_by_id("cin-001")

    assert row == {
        "id": "cin-001",
        "name": "Cinema One",
        "address": "1 Rue",
        "city": "Montréal",
        "website": None,
    }


@pytest.mark.asyncio
async def test_find_by_id_returns_none_when_missing(
    reader: PostgresCinemaReadGateway,
) -> None:
    """An unknown cinema ID returns None."""
    assert await reader.find_by_id("missing") is None
