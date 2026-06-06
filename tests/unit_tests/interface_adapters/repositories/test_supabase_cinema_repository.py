"""Unit tests for SupabaseCinemaRepository with mocked gateway."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.exceptions import CinemaIdAlreadyExistsError
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId
from marquise.interface_adapters.repositories.protocols.cinema import (
    CinemaGateway,
    GatewayError,
)
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)


@pytest.fixture
def mock_gateway() -> AsyncMock:
    """Provide a mocked CinemaGateway."""
    return create_autospec(CinemaGateway, instance=True)


@pytest.fixture
def repo(mock_gateway: AsyncMock) -> SupabaseCinemaRepository:
    """Provide a SupabaseCinemaRepository wired to the mock gateway."""
    return SupabaseCinemaRepository(gateway=mock_gateway)


@pytest.mark.asyncio
async def test_save(repo: SupabaseCinemaRepository, mock_gateway: AsyncMock) -> None:
    """Verify save delegates to the gateway and maps the result."""
    mock_gateway.save.return_value = {
        "id": "cin-001",
        "name": "Test Cinema",
        "address": "123 Test St",
        "city": "Montreal",
    }

    cinema = Cinema(
        id=CinemaId(value="cin-001"),
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
    )
    result = await repo.save(cinema)

    assert result.id == CinemaId(value="cin-001")
    assert result.name == "Test Cinema"
    mock_gateway.save.assert_awaited_once_with(
        cinema_id="cin-001", name="Test Cinema", address="123 Test St", city="Montreal"
    )


@pytest.mark.asyncio
async def test_save_raises_cinema_id_already_exists_on_gateway_error(
    repo: SupabaseCinemaRepository, mock_gateway: AsyncMock
) -> None:
    """Verify save wraps GatewayError as CinemaIdAlreadyExistsError."""
    mock_gateway.save.side_effect = GatewayError("ID collision")

    cinema = Cinema(
        id=CinemaId(value="cin-001"),
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
    )

    with pytest.raises(CinemaIdAlreadyExistsError, match="ID collision"):
        await repo.save(cinema)


@pytest.mark.asyncio
async def test_find_by_id(
    repo: SupabaseCinemaRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_id delegates to the gateway and maps the result."""
    mock_gateway.find_by_id.return_value = {
        "id": "cin-001",
        "name": "Test",
        "address": "123",
        "city": "Montreal",
    }

    result = await repo.find_by_id(CinemaId(value="cin-001"))

    assert result is not None
    assert result.id == CinemaId(value="cin-001")


@pytest.mark.asyncio
async def test_find_by_id_missing(
    repo: SupabaseCinemaRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_id returns None when the gateway returns None."""
    mock_gateway.find_by_id.return_value = None

    result = await repo.find_by_id(CinemaId(value="cin-missing"))

    assert result is None


@pytest.mark.asyncio
async def test_find_by_name_and_address(
    repo: SupabaseCinemaRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_name_and_address delegates and maps correctly."""
    mock_gateway.find_by_name_and_address.return_value = {
        "id": "cin-001",
        "name": "Unique",
        "address": "456 Ave",
        "city": "Montreal",
    }

    result = await repo.find_by_name_and_address(name="Unique", address="456 Ave")

    assert result is not None
    assert result.name == "Unique"


@pytest.mark.asyncio
async def test_find_by_name_and_address_missing(
    repo: SupabaseCinemaRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_name_and_address returns None when not found."""
    mock_gateway.find_by_name_and_address.return_value = None

    result = await repo.find_by_name_and_address(name="Missing", address="Nowhere")

    assert result is None


@pytest.mark.asyncio
async def test_exists_by_id(
    repo: SupabaseCinemaRepository, mock_gateway: AsyncMock
) -> None:
    """Verify exists_by_id returns True when the gateway returns True."""
    mock_gateway.exists_by_id.return_value = True

    result = await repo.exists_by_id(CinemaId(value="cin-exists"))

    assert result is True


@pytest.mark.asyncio
async def test_exists_by_id_missing(
    repo: SupabaseCinemaRepository, mock_gateway: AsyncMock
) -> None:
    """Verify exists_by_id returns False when the gateway returns False."""
    mock_gateway.exists_by_id.return_value = False

    result = await repo.exists_by_id(CinemaId(value="cin-missing"))

    assert result is False
