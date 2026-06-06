"""Integration tests for SupabaseCinemaGateway."""

from __future__ import annotations

import pytest

from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway


@pytest.mark.asyncio
async def test_save_and_find_by_id(gateway: SupabaseCinemaGateway) -> None:
    """Verify a cinema can be saved and then retrieved by ID."""
    result = await gateway.save(
        cinema_id="cin-001",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
    )
    assert result["id"] == "cin-001"
    assert result["name"] == "Test Cinema"

    found = await gateway.find_by_id("cin-001")
    assert found is not None
    assert found["name"] == "Test Cinema"


@pytest.mark.asyncio
async def test_save_and_find_by_name_and_address(
    gateway: SupabaseCinemaGateway,
) -> None:
    """Verify a cinema can be saved and found by name and address."""
    await gateway.save(
        cinema_id="cin-002",
        name="Unique Cinema",
        address="456 Unique Ave",
        city="Montreal",
    )

    found = await gateway.find_by_name_and_address(
        name="Unique Cinema", address="456 Unique Ave"
    )
    assert found is not None
    assert found["id"] == "cin-002"


@pytest.mark.asyncio
async def test_find_by_name_and_address_with_none_address(
    gateway: SupabaseCinemaGateway,
) -> None:
    """Verify lookups work when address is None."""
    await gateway.save(
        cinema_id="cin-003",
        name="No Address Cinema",
        address=None,
        city="Montreal",
    )

    found = await gateway.find_by_name_and_address(
        name="No Address Cinema", address=None
    )
    assert found is not None
    assert found["id"] == "cin-003"


@pytest.mark.asyncio
async def test_exists_by_id(gateway: SupabaseCinemaGateway) -> None:
    """Verify exists_by_id returns correct results."""
    await gateway.save(
        cinema_id="cin-004",
        name="Existing Cinema",
        address="789 Exist Rd",
        city="Montreal",
    )

    assert await gateway.exists_by_id("cin-004") is True
    assert await gateway.exists_by_id("cin-nonexistent") is False


@pytest.mark.asyncio
async def test_find_by_id_missing(gateway: SupabaseCinemaGateway) -> None:
    """Verify find_by_id returns None for a non-existent ID."""
    found = await gateway.find_by_id("cin-missing")
    assert found is None


@pytest.mark.asyncio
async def test_find_by_name_and_address_missing(
    gateway: SupabaseCinemaGateway,
) -> None:
    """Verify find_by_name_and_address returns None for a non-existent cinema."""
    found = await gateway.find_by_name_and_address(
        name="Non Existent", address="Nowhere"
    )
    assert found is None


@pytest.mark.asyncio
async def test_save_updates_existing(gateway: SupabaseCinemaGateway) -> None:
    """Verify save upserts (updates) an existing cinema."""
    await gateway.save(
        cinema_id="cin-005",
        name="Original Name",
        address="100 Original St",
        city="Montreal",
    )

    saved = await gateway.save(
        cinema_id="cin-005",
        name="Updated Name",
        address="200 Updated Ave",
        city="Quebec",
    )
    assert saved["name"] == "Updated Name"
    assert saved["city"] == "Quebec"

    found = await gateway.find_by_id("cin-005")
    assert found is not None
    assert found["name"] == "Updated Name"
