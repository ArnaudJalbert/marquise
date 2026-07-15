"""Unit tests for SupabaseSourceDefinitionRepository with mocked gateway."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.exceptions import SourceAlreadyExistsError
from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName
from marquise.interface_adapters.repositories.protocols.cinema import GatewayError
from marquise.interface_adapters.repositories.protocols.source_definition import (
    SourceDefinitionGateway,
)
from marquise.interface_adapters.repositories.supabase.source_definition_repository import (  # noqa: E501
    SupabaseSourceDefinitionRepository,
)


@pytest.fixture
def mock_gateway() -> AsyncMock:
    """Provide a mocked SourceDefinitionGateway."""
    return create_autospec(SourceDefinitionGateway, instance=True)


@pytest.fixture
def repo(
    mock_gateway: AsyncMock,
) -> SupabaseSourceDefinitionRepository:
    """Provide a SupabaseSourceDefinitionRepository wired to the mock gateway."""
    return SupabaseSourceDefinitionRepository(gateway=mock_gateway)


def _gateway_row(
    name: str = "cineplex",
    display_name: str = "Cineplex",
    description: str | None = None,
) -> dict:
    return {
        "name": name,
        "display_name": display_name,
        "description": description,
    }


@pytest.mark.asyncio
async def test_save(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify save delegates to the gateway and maps the result."""
    mock_gateway.save.return_value = _gateway_row()

    source = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
    )
    result = await repo.save(source)

    assert result.name == SourceName(value="cineplex")
    assert result.display_name == "Cineplex"
    mock_gateway.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_raises_on_gateway_error(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify save wraps GatewayError as SourceAlreadyExistsError."""
    mock_gateway.save.side_effect = GatewayError("name collision")

    source = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
    )
    with pytest.raises(SourceAlreadyExistsError, match="name collision"):
        await repo.save(source)


@pytest.mark.asyncio
async def test_find_by_name(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_name delegates to the gateway and maps the result."""
    mock_gateway.find_by_name.return_value = _gateway_row()

    result = await repo.find_by_name(SourceName(value="cineplex"))

    assert result is not None
    assert result.name == SourceName(value="cineplex")
    mock_gateway.find_by_name.assert_awaited_once_with("cineplex")


@pytest.mark.asyncio
async def test_find_by_name_missing(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_name returns None when the gateway returns None."""
    mock_gateway.find_by_name.return_value = None

    result = await repo.find_by_name(SourceName(value="missing"))

    assert result is None


@pytest.mark.asyncio
async def test_find_all(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_all returns all mapped source definitions."""
    mock_gateway.find_all.return_value = [
        _gateway_row(name="cineplex", display_name="Cineplex"),
        _gateway_row(name="cinema_du_parc", display_name="Cinema du Parc"),
    ]

    result = await repo.find_all()

    assert len(result) == 2
    assert result[0].name == SourceName(value="cineplex")
    assert result[1].name == SourceName(value="cinema_du_parc")
    mock_gateway.find_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_all_empty(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_all returns empty list when no sources exist."""
    mock_gateway.find_all.return_value = []

    result = await repo.find_all()
    assert result == []


@pytest.mark.asyncio
async def test_delete_delegates_to_gateway(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify delete delegates to the gateway and returns True."""
    mock_gateway.delete.return_value = True

    result = await repo.delete(SourceName(value="cineplex"))
    assert result is True
    mock_gateway.delete.assert_awaited_once_with("cineplex")


@pytest.mark.asyncio
async def test_delete_missing(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify delete returns False when the gateway returns False."""
    mock_gateway.delete.return_value = False

    result = await repo.delete(SourceName(value="missing"))
    assert result is False


@pytest.mark.asyncio
async def test_exists_by_name(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify exists_by_name returns True when gateway returns True."""
    mock_gateway.exists_by_name.return_value = True

    result = await repo.exists_by_name(SourceName(value="cineplex"))
    assert result is True


@pytest.mark.asyncio
async def test_exists_by_name_missing(
    repo: SupabaseSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify exists_by_name returns False when gateway returns False."""
    mock_gateway.exists_by_name.return_value = False

    result = await repo.exists_by_name(SourceName(value="missing"))
    assert result is False
