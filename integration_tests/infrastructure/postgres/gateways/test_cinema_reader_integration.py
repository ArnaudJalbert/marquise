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


@pytest.mark.asyncio
async def test_search_with_limit_and_offset_returns_correct_slice_and_total(
    reader: PostgresCinemaReadGateway, gateway: PostgresCinemaGateway
) -> None:
    """Verify limit/offset return the correct page while total reflects all rows."""
    for i in range(5):
        await gateway.save(
            cinema_id=f"cin-page-{i}",
            name=f"Page Cinema {i}",
            address=None,
            city="Montreal",
            website=None,
        )

    page = await reader.search(name_filter=None, limit=2, offset=1)

    assert page.total == 5
    assert [row["name"] for row in page.rows] == [
        "Page Cinema 1",
        "Page Cinema 2",
    ]


@pytest.mark.asyncio
async def test_search_offset_past_total_returns_empty_rows_with_correct_total(
    reader: PostgresCinemaReadGateway, gateway: PostgresCinemaGateway
) -> None:
    """Verify an offset beyond the result set returns no rows but the true total.

    Exercises the fallback COUNT(*) path: when LIMIT/OFFSET returns zero
    rows, there is no row to read a windowed total off, so the gateway must
    fall back to a separate count query.
    """
    for i in range(2):
        await gateway.save(
            cinema_id=f"cin-past-{i}",
            name=f"Past Cinema {i}",
            address=None,
            city="Montreal",
            website=None,
        )

    page = await reader.search(name_filter=None, limit=10, offset=100)

    assert page.rows == []
    assert page.total == 2


@pytest.mark.asyncio
async def test_search_with_name_filter_and_limit(
    reader: PostgresCinemaReadGateway, gateway: PostgresCinemaGateway
) -> None:
    """Verify name_filter and limit/offset combine correctly."""
    await gateway.save(
        cinema_id="cin-match-1",
        name="Cineplex Downtown",
        address=None,
        city="Montreal",
        website=None,
    )
    await gateway.save(
        cinema_id="cin-match-2",
        name="Cineplex Uptown",
        address=None,
        city="Montreal",
        website=None,
    )
    await gateway.save(
        cinema_id="cin-nomatch",
        name="Landmark Cinemas",
        address=None,
        city="Montreal",
        website=None,
    )

    page = await reader.search(name_filter="cineplex", limit=1, offset=0)

    assert page.total == 2
    assert len(page.rows) == 1
    assert page.rows[0]["name"] == "Cineplex Downtown"
