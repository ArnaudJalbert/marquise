"""Unit tests for PostgresSourceDefinitionRepository with mocked gateway."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.exceptions import SourceAlreadyExistsError
from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName
from marquise.interface_adapters.gateways.base import GatewayError
from marquise.interface_adapters.gateways.source_definition import (
    SourceDefinitionGateway,
)
from marquise.interface_adapters.repositories.source_definition_repository import (  # noqa: E501
    PostgresSourceDefinitionRepository,
)


@pytest.fixture
def mock_gateway() -> AsyncMock:
    """Provide a mocked SourceDefinitionGateway."""
    return create_autospec(SourceDefinitionGateway, instance=True)


@pytest.fixture
def repo(
    mock_gateway: AsyncMock,
) -> PostgresSourceDefinitionRepository:
    """Provide a PostgresSourceDefinitionRepository wired to the mock gateway."""
    return PostgresSourceDefinitionRepository(gateway=mock_gateway)


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
    repo: PostgresSourceDefinitionRepository, mock_gateway: AsyncMock
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
    repo: PostgresSourceDefinitionRepository, mock_gateway: AsyncMock
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
    repo: PostgresSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_name delegates to the gateway and maps the result."""
    mock_gateway.find_by_name.return_value = _gateway_row()

    result = await repo.find_by_name(SourceName(value="cineplex"))

    assert result is not None
    assert result.name == SourceName(value="cineplex")
    mock_gateway.find_by_name.assert_awaited_once_with("cineplex")


@pytest.mark.asyncio
async def test_find_by_name_missing(
    repo: PostgresSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_name returns None when the gateway returns None."""
    mock_gateway.find_by_name.return_value = None

    result = await repo.find_by_name(SourceName(value="missing"))

    assert result is None


@pytest.mark.asyncio
async def test_delete_delegates_to_gateway(
    repo: PostgresSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify delete delegates to the gateway and returns True."""
    mock_gateway.delete.return_value = True

    result = await repo.delete(SourceName(value="cineplex"))
    assert result is True
    mock_gateway.delete.assert_awaited_once_with("cineplex")


@pytest.mark.asyncio
async def test_delete_missing(
    repo: PostgresSourceDefinitionRepository, mock_gateway: AsyncMock
) -> None:
    """Verify delete returns False when the gateway returns False."""
    mock_gateway.delete.return_value = False

    result = await repo.delete(SourceName(value="missing"))
    assert result is False
