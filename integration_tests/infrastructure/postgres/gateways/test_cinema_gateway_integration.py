"""Integration tests for PostgresCinemaGateway."""

from __future__ import annotations

import pytest

from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway


@pytest.mark.asyncio
async def test_save_and_find_by_id(gateway: PostgresCinemaGateway) -> None:
    """Verify a cinema can be saved and then retrieved by ID."""
    result = await gateway.save(
        cinema_id="cin-001",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )
    assert result["id"] == "cin-001"
    assert result["name"] == "Test Cinema"
    assert result["website"] == "https://example.com"

    found = await gateway.find_by_id("cin-001")
    assert found is not None
    assert found["name"] == "Test Cinema"
    assert found["website"] == "https://example.com"


@pytest.mark.asyncio
async def test_save_and_find_by_name_and_address(
    gateway: PostgresCinemaGateway,
) -> None:
    """Verify a cinema can be saved and found by name and address."""
    await gateway.save(
        cinema_id="cin-002",
        name="Unique Cinema",
        address="456 Unique Ave",
        city="Montreal",
        website="https://unique.example.com",
    )

    found = await gateway.find_by_name_and_address(
        name="Unique Cinema", address="456 Unique Ave"
    )
    assert found is not None
    assert found["id"] == "cin-002"
    assert found["website"] == "https://unique.example.com"


@pytest.mark.asyncio
async def test_find_by_name_and_address_with_none_address(
    gateway: PostgresCinemaGateway,
) -> None:
    """Verify lookups work when address is None."""
    await gateway.save(
        cinema_id="cin-003",
        name="No Address Cinema",
        address=None,
        city="Montreal",
        website=None,
    )

    found = await gateway.find_by_name_and_address(
        name="No Address Cinema", address=None
    )
    assert found is not None
    assert found["id"] == "cin-003"
    assert found["website"] is None


@pytest.mark.asyncio
async def test_exists_by_id(gateway: PostgresCinemaGateway) -> None:
    """Verify exists_by_id returns correct results."""
    await gateway.save(
        cinema_id="cin-004",
        name="Existing Cinema",
        address="789 Exist Rd",
        city="Montreal",
        website="https://existing.example.com",
    )

    assert await gateway.exists_by_id("cin-004") is True
    assert await gateway.exists_by_id("cin-nonexistent") is False


@pytest.mark.asyncio
async def test_find_by_id_missing(gateway: PostgresCinemaGateway) -> None:
    """Verify find_by_id returns None for a non-existent ID."""
    found = await gateway.find_by_id("cin-missing")
    assert found is None


@pytest.mark.asyncio
async def test_find_by_name_and_address_missing(
    gateway: PostgresCinemaGateway,
) -> None:
    """Verify find_by_name_and_address returns None for a non-existent cinema."""
    found = await gateway.find_by_name_and_address(
        name="Non Existent", address="Nowhere"
    )
    assert found is None


@pytest.mark.asyncio
async def test_save_updates_existing(gateway: PostgresCinemaGateway) -> None:
    """Verify save upserts (updates) an existing cinema."""
    await gateway.save(
        cinema_id="cin-005",
        name="Original Name",
        address="100 Original St",
        city="Montreal",
        website="https://original.example.com",
    )

    saved = await gateway.save(
        cinema_id="cin-005",
        name="Updated Name",
        address="200 Updated Ave",
        city="Quebec",
        website="https://updated.example.com",
    )
    assert saved["name"] == "Updated Name"
    assert saved["city"] == "Quebec"
    assert saved["website"] == "https://updated.example.com"

    found = await gateway.find_by_id("cin-005")
    assert found is not None
    assert found["name"] == "Updated Name"
    assert found["website"] == "https://updated.example.com"
