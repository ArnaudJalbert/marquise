"""Integration tests for SupabaseScreeningGateway."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)


@pytest.mark.asyncio
async def test_save_and_find_by_id(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify a screening can be saved and then retrieved by ID."""
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc)
    result = await screening_gateway.save(
        screening_id="scr-001",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
        price=14.99,
    )
    assert result["id"] == "scr-001"
    assert result["movie_id"] == "mov-001"
    assert result["cinema_id"] == "cin-001"
    assert result["price"] == 14.99

    found = await screening_gateway.find_by_id("scr-001")
    assert found is not None
    assert found["movie_id"] == "mov-001"
    assert found["price"] == 14.99


@pytest.mark.asyncio
async def test_find_by_id_missing(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify find_by_id returns None for a non-existent ID."""
    found = await screening_gateway.find_by_id("scr-missing")
    assert found is None


@pytest.mark.asyncio
async def test_find_by_cinema_and_date_range(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify screenings can be found within a date range for a cinema."""
    await screening_gateway.save(
        screening_id="scr-003",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=timezone.utc),
        price=10.0,
    )
    await screening_gateway.save(
        screening_id="scr-004",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=timezone.utc),
        price=12.0,
    )
    await screening_gateway.save(
        screening_id="scr-005",
        movie_id="mov-003",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 10, 21, 0, 0, tzinfo=timezone.utc),
        price=15.0,
    )

    found = await screening_gateway.find_by_cinema_and_date_range(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 8, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert len(found) == 2
    assert found[0]["id"] == "scr-003"
    assert found[1]["id"] == "scr-004"


@pytest.mark.asyncio
async def test_find_by_cinema_and_date_range_empty(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify find_by_cinema_and_date_range returns empty list when no match."""
    found = await screening_gateway.find_by_cinema_and_date_range(
        cinema_id="cin-empty",
        start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert found == []


@pytest.mark.asyncio
async def test_save_upserts_on_unique_key_conflict(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify save updates price on conflict and preserves the existing ID."""
    showtime = datetime(2026, 6, 9, 19, 30, 0, tzinfo=timezone.utc)
    await screening_gateway.save(
        screening_id="scr-006",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
        price=10.0,
    )

    saved = await screening_gateway.save(
        screening_id="scr-007",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
        price=15.0,
    )
    assert saved["price"] == 15.0
    assert saved["id"] == "scr-006"
    assert saved.get("__inserted") is False

    found = await screening_gateway.find_by_id("scr-006")
    assert found is not None
    assert found["price"] == 15.0

    new_id = await screening_gateway.find_by_id("scr-007")
    assert new_id is None
